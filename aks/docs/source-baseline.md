# AKS source baseline

The independent AKS source was seeded from K3S commit `6ca720be871727c240259664d9c1d1515766f42d` after K3S tasks 1–6 and F1–F4 were complete.

Copied paths:

- `k3s/apps/` to `aks/apps/` (API, worker, frontend, their tests and lockfiles)
- `k3s/k8s/` to `aks/k8s/`, excluding all previously sealed K3S ciphertext
- `k3s/argocd/` to `aks/argocd/`
- `k3s/dashboards/` to `aks/dashboards/`
- the ArgoCD, KEDA, SealedSecrets, monitoring, MinIO, and compose gateway inputs under `k3s/infra/`
- `k3s/loadtest/` to `aks/loadtest/`
- the image selection, tag, release, smoke, persistence, and observability helpers plus their tests from `k3s/scripts/`
- `k3s/docker-compose.yaml` to `aks/docker-compose.yaml`

Excluded inputs include `.env` files, virtual environments, kubeconfig files, private keys, generated data, VM provisioning and access scripts, K3S bootstrap scripts, and all K3S SealedSecret ciphertext. AKS secret ciphertext will be generated with a new AKS key in A6. No Azure resource or credential was created as part of A1.
