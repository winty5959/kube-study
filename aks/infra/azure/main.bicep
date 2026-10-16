targetScope = 'resourceGroup'

@description('Name of the AKS cluster.')
param clusterName string = 'aks-kube-study'

@description('Azure region for the test cluster.')
param location string = resourceGroup().location

@description('A currently reachable management IPv4 CIDR. Use the workstation egress IP as /32.')
param apiServerAuthorizedIpRanges array

@description('Use the current supported patch release from the target region.')
param kubernetesVersion string = '1.36'

@description('System pool VM size selected for this subscription.')
param nodeVmSize string = 'Standard_D4as_v5'

@description('New address space owned by the AKS test cluster.')
param virtualNetworkPrefix string = '10.240.0.0/16'

@description('Subnet for the two system nodes.')
param nodeSubnetPrefix string = '10.240.0.0/22'

@description('Azure CNI Overlay pod range.')
param podCidr string = '10.244.0.0/16'

@description('Kubernetes service range.')
param serviceCidr string = '10.250.0.0/16'

@description('Kubernetes DNS service IP within serviceCidr.')
param dnsServiceIp string = '10.250.0.10'

var tags = {
  project: 'kube-study'
  environment: 'test'
  managedBy: 'bicep'
}

var networkContributorRoleId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '4d97b98b-1d4f-4787-a291-c67834d212e7'
)

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2025-01-01' = {
  name: 'aks-kube-study-vnet'
  location: location
  tags: tags
  properties: {
    privateEndpointVNetPolicies: 'Disabled'
    addressSpace: {
      addressPrefixes: [virtualNetworkPrefix]
    }
  }
}

resource nodeSubnet 'Microsoft.Network/virtualNetworks/subnets@2025-05-01' = {
  parent: virtualNetwork
  name: 'aks-nodes'
  properties: {
    addressPrefix: nodeSubnetPrefix
    privateEndpointNetworkPolicies: 'Disabled'
  }
}

resource controlPlaneIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' = {
  name: 'aks-kube-study-controlplane'
  location: location
  tags: tags
  properties: {
    isolationScope: 'None'
  }
}

resource subnetNetworkContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  scope: nodeSubnet
  name: guid(nodeSubnet.id, controlPlaneIdentity.id, networkContributorRoleId)
  properties: {
    roleDefinitionId: networkContributorRoleId
    principalId: controlPlaneIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource cluster 'Microsoft.ContainerService/managedClusters@2026-03-01' = {
  name: clusterName
  location: location
  kind: 'Base'
  tags: tags
  sku: {
    name: 'Base'
    tier: 'Free'
  }
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${controlPlaneIdentity.id}': {}
    }
  }
  properties: {
    aadProfile: {
      managed: true
      enableAzureRBAC: true
    }
    agentPoolProfiles: [
      {
        name: 'system'
        mode: 'System'
        type: 'VirtualMachineScaleSets'
        count: 2
        vmSize: nodeVmSize
        osSKU: 'Ubuntu'
        osDiskType: 'Managed'
        osDiskSizeGB: 64
        maxPods: 50
        enableFIPS: false
        enableNodePublicIP: false
        kubeletDiskType: 'OS'
        scaleDownMode: 'Delete'
        vnetSubnetID: nodeSubnet.id
        enableAutoScaling: false
        upgradeSettings: {
          maxUnavailable: '0'
          maxSurge: '1'
        }
        securityProfile: {
          enableSecureBoot: false
          enableVTPM: false
          sshAccess: 'LocalUser'
        }
      }
    ]
    apiServerAccessProfile: {
      enablePrivateCluster: false
      authorizedIPRanges: apiServerAuthorizedIpRanges
    }
    autoUpgradeProfile: {
      upgradeChannel: 'patch'
      nodeOSUpgradeChannel: 'SecurityPatch'
    }
    disableLocalAccounts: true
    dnsPrefix: '${clusterName}-${uniqueString(subscription().id, resourceGroup().id)}'
    enableRBAC: true
    kubernetesVersion: kubernetesVersion
    networkProfile: {
      networkPlugin: 'azure'
      networkPluginMode: 'overlay'
      networkDataplane: 'cilium'
      networkPolicy: 'cilium'
      podCidr: podCidr
      serviceCidr: serviceCidr
      dnsServiceIP: dnsServiceIp
      outboundType: 'loadBalancer'
      loadBalancerSku: 'standard'
      loadBalancerProfile: {
        managedOutboundIPs: {
          count: 1
        }
      }
    }
    nodeProvisioningProfile: {
      mode: 'Manual'
    }
    metricsProfile: {
      costAnalysis: {
        enabled: false
      }
    }
    oidcIssuerProfile: {
      enabled: true
    }
    storageProfile: {
      diskCSIDriver: {
        enabled: true
      }
      fileCSIDriver: {
        enabled: true
      }
      snapshotController: {
        enabled: true
      }
    }
    supportPlan: 'KubernetesOfficial'
  }
  dependsOn: [
    subnetNetworkContributor
  ]
}

output clusterId string = cluster.id
output clusterName string = cluster.name
output nodeResourceGroup string = cluster.properties.nodeResourceGroup
output apiServerFqdn string = cluster.properties.fqdn
