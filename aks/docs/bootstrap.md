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

## Platform bootstrap (A6)

The AKS dev platform uses the chart versions already pinned in the Argo sources and K3S bootstrap:

| Release | Chart | Version | App version | AKS 1.36 result |
|---|---|---:|---:|---|
| sealed-secrets | sealed-secrets | 2.20.0 | 0.40.0 | Installed and Ready |
| keda | keda | 2.21.0 | 2.21.0 | Helm revision 4 deployed; operator, metrics API, and CRDs Ready |
| monitoring | kube-prometheus-stack | 92.7.0 | 0.94.1 | Installed; Prometheus, Alertmanager, Grafana, and node exporter Ready |
| argocd | argo-cd | 10.10.3 | 3.5.5 | Installed; server, repo-server, controller, and Redis Ready |

All four chart `kubeVersion` constraints include AKS Kubernetes 1.36.4. Helm renders completed with
the repository values; no chart version change was needed. The Argo CD values include a
SealedSecret health check so later bootstrap waves wait for decryption. The root Application has
not been applied yet; A7 adopts these existing releases before app auto-sync is enabled.

Helm 4's server-side KEDA upgrade and rollback conflicted with the six validating-webhook
`namespaceSelector` fields owned by AKS's `admissionsenforcer`. Reapplying the pinned chart with
`--server-side=false` completed revision 4 without removing those selectors. The bootstrap script
checks release status as well as chart version, and Argo becomes the sole reconciler in A7.

Run `aks/scripts/install-gitops.sh`, then apply the data-only AKS platform source with
`kubectl --kubeconfig aks/infra/azure/local/kubeconfig --context aks-study -n album-dev apply -k aks/k8s/gitops/dev/platform`,
followed by `aks/scripts/install-keda.sh` and `aks/scripts/install-monitoring.sh dev`. The GitOps
script installs SealedSecrets before sealing, verifies its key backup, and installs Argo CD. The
monitoring script reuses the same sealing step before installing Grafana.

`aks/scripts/seal-environment.sh dev` creates independent random AKS dev credentials in
`~/.local/share/kube-study/aks-dev-secrets.env` with mode `0600`. Its AKS-only key bundle is
`~/.local/share/kube-study/sealed-secrets-key-aks-dev.yaml`, also mode `0600`; the containing
directory is mode `0700`. These files are outside Git. The manifests under
`aks/k8s/secrets/dev/` contain strict name-and-namespace ciphertext for `album-dev/album-secrets`
and `monitoring/grafana-admin`. GHCR images are public, so no registry Secret or long-lived
`GITHUB_TOKEN` is used. The SealedSecret condition and required key names were checked without
printing secret data. Reusing the dev scope ciphertext in a different namespace created no Secret.

At bootstrap, PostgreSQL, Redis, and MinIO each reached Ready and their 2Gi, 1Gi, and 10Gi claims
bound. Prometheus, Grafana, and Alertmanager also reached Ready, and their 5Gi, 1Gi, and 1Gi claims
bound. All six claims use `album-standard-ssd-retain` (`StandardSSD_LRS`, `Retain`). AKS reports
3860m CPU and about 14.49Gi memory allocatable per D4as_v5 node. Including all live containers,
init containers, and the two node-exporter DaemonSet Pods, current requests are 1330m/2.28Gi on one
node and 1147m/1.34Gi on the other. A contemporaneous `kubectl top nodes` sample was 180m/1951Mi
and 187m/1962Mi. These are the idle platform baseline; A10 must repeat the 80% per-node request
limit under the full app and load scenarios.
