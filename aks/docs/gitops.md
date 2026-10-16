# AKS GitOps

AKS runs an independent Argo CD in `argocd`. Its root Application reads only
`aks/argocd/bootstrap/dev` from the repository's `main` branch. K3S Argo CD does not register or
manage this cluster.

## Bootstrap order

`root-dev` creates these child Applications in sync-wave order:

| Wave | Application | Ownership |
|---:|---|---|
| -3 | `sealed-secrets-dev` | Pinned SealedSecrets Helm release |
| -3 | `keda-dev` | Pinned KEDA Helm release |
| -2 | `credentials-dev` | AKS-only dev SealedSecrets and namespaces |
| -1 | `platform-dev` | Traefik Helm chart, Azure Disk StorageClass, and data services |
| 0 | `monitoring-dev` | kube-prometheus-stack Helm release |
| 1 | `observability-dev` | Dashboards and monitoring resources |

The child-Application health customization makes the root wait for each child to report Synced
before proceeding. The album application is added in A8, after its migration and smoke hooks are
ready. The data services remain available while the application child is absent.

`platform-dev` combines the pinned Traefik chart with the Kustomize source at
`aks/k8s/gitops/dev/platform`. Its destination namespace is `ingress-system`, which is Traefik's
release namespace; the Kustomize resources explicitly keep `album-dev` where required. The Git
source also supplies `$values/aks/infra/traefik/values.yaml`. Argo CD uses Helm to render the
existing `traefik` release name, so it does not install another controller or create a second Helm
release. Annotation resource tracking lets Argo take ownership of the existing resources.

## Apply and inspect

Push the validated commit to `main` so the remote repository contains every source before applying
the root. The root has automated sync enabled; applying it starts the child Applications.

```sh
PATH="$HOME/.azure/bin:$PATH" kubectl \
  --kubeconfig aks/infra/azure/local/kubeconfig --context aks-study \
  apply -f aks/argocd/root-dev.yaml

PATH="$HOME/.azure/bin:$PATH" kubectl \
  --kubeconfig aks/infra/azure/local/kubeconfig --context aks-study \
  get applications -n argocd
```

Check `SYNC STATUS` and `HEALTH STATUS` for every child. `platform-dev` must be Synced and Healthy,
and the live Helm inventory must contain exactly one Traefik release in `ingress-system`. The
platform source also adopts the already-bound StorageClass and the three data StatefulSets. Do not
uninstall a Helm release or delete a PVC to resolve an ownership difference.
`platform-dev` uses server-side diff so API-defaulted StatefulSet fields compare against the same
values the API server stores.
Traefik publishes its internal Service DNS hostname to Ingress status. The ClusterIP service remains
private, and no public ingress address is created.

KEDA's validating webhook includes namespace selectors managed by AKS's `admissionsenforcer`.
The KEDA Application ignores only fields owned by that manager on `keda-admission`, and uses
`RespectIgnoreDifferences=true` so sync preserves them. The standalone bootstrap script uses Helm
client-side apply for that release. After Argo takes ownership, use the Application as the sole
reconciler and inspect its diff before changing the webhook configuration.

## Stop and resume the learning cluster

```sh
PATH="$HOME/.azure/bin:$PATH" az aks stop -g rg-seonung-aks-test -n aks-kube-study
PATH="$HOME/.azure/bin:$PATH" az aks start -g rg-seonung-aks-test -n aks-kube-study
```

Stopping releases the node compute allocation. Azure Disk and other retained resources continue to
accrue charges. After starting, wait for the AKS operation to reach `Succeeded` and for the API
endpoint to resolve before using `kubectl` or Helm.
