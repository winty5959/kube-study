# AKS bootstrap

The test cluster lives in `rg-seonung-aks-test` in `koreacentral`. The deployment uses
the selected `Standard_D4as_v5` SKU, two system nodes, an isolated VNet, Azure CNI Overlay
with Cilium, Microsoft Entra/Azure RBAC, disabled local accounts, and a public API endpoint
restricted to the current management workstation's IPv4 `/32`.

## Preview and deploy

Run from the repository root after signing in to the Enterprise architecture task subscription.
The selected resource group is separate from the existing K3S group. The authorized range below
is computed at runtime and is not written to Git or printed by the commands.

```bash
AKS_API_IP="$(curl -4fsS https://api.ipify.org)"
AKS_API_RANGE="${AKS_API_IP}/32"

az deployment group what-if \
  --resource-group rg-seonung-aks-test \
  --template-file aks/infra/azure/main.bicep \
  --parameters apiServerAuthorizedIpRanges="[\"${AKS_API_RANGE}\"]"

az deployment group create \
  --name aks-kube-study \
  --resource-group rg-seonung-aks-test \
  --template-file aks/infra/azure/main.bicep \
  --parameters apiServerAuthorizedIpRanges="[\"${AKS_API_RANGE}\"]"
```

The Bicep example parameter file uses a documentation-only IP range. Do not use it for a real
deployment. The live deployment command passes the current workstation range directly and keeps
it out of tracked files. If the workstation's egress address changes, update AKS API server
authorized ranges before using `kubectl` again.

The first deployment has already completed. On later runs, inspect the complete `what-if` output
before deploying. ARM reports some AKS provider-generated fields and the identity principal
expression as property-level changes even when the actual role assignment matches the control-plane
identity. Do not apply a repeat deployment while those changes are unexplained; the successful
initial deployment and current cluster settings are recorded in the A3 evidence.

## Grant Kubernetes access and connect

Azure resource Contributor/Owner permissions and Kubernetes API authorization are separate. The
deployment disables local admin accounts and enables Azure RBAC. An Owner can assign the signed-in
Entra user the least-scope roles needed for this test cluster:

```bash
AKS_ID="$(az aks show --resource-group rg-seonung-aks-test --name aks-kube-study --query id -o tsv)"
USER_ID="$(az ad signed-in-user show --query id -o tsv)"

az role assignment create \
  --assignee-object-id "$USER_ID" \
  --assignee-principal-type User \
  --role "Azure Kubernetes Service Cluster User Role" \
  --scope "$AKS_ID"

az role assignment create \
  --assignee-object-id "$USER_ID" \
  --assignee-principal-type User \
  --role "Azure Kubernetes Service RBAC Cluster Admin" \
  --scope "$AKS_ID"
```

Keep the AKS kubeconfig separate from any existing K3S context:

```bash
mkdir -p aks/infra/azure/local
az aks get-credentials \
  --resource-group rg-seonung-aks-test \
  --name aks-kube-study \
  --file aks/infra/azure/local/kubeconfig
kubelogin convert-kubeconfig -l azurecli --kubeconfig aks/infra/azure/local/kubeconfig
KUBECONFIG="$PWD/aks/infra/azure/local/kubeconfig" kubectl get nodes -o wide
```

`kubelogin` is required for Entra-backed authentication. Local kubeconfig files and generated
deployment parameters are excluded from Git. The cluster auto-upgrade policy accepts patch
upgrades and security-only node OS updates; review cluster health after each maintenance cycle and
repeat the node-drain/storage checks in A11 after a Kubernetes minor upgrade.
