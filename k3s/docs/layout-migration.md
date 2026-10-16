# K3S repository layout migration

Date: 2026-10-16 KST

## Result

The existing K3S photo album project now lives entirely under `k3s/`. The repository root
contains the project index, repository controls, and the independent `aks/` roadmap. Both
`k3s/` and `aks/` resolve to this same Git root.

The dev and prod ArgoCD root Applications now watch `k3s/argocd/bootstrap/{dev,prod}`.
Each cluster has eight Synced/Healthy Applications. Five Git source paths per cluster start
with `k3s/`; Helm value references use `$values/k3s/infra/`. KEDA, monitoring, and Sealed
Secrets remain pathless external chart sources at their existing pinned versions.

## Transition record

1. The K3S tree, workflows, helpers, VM sync path, docs, and temporary source bridges were
   committed and pushed to the existing `main` branch. No force push or new repository was used.
2. GitHub Actions run [38842930641](https://github.com/winty5959/kube-study/actions/runs/38842930641)
   built API, worker, frontend, and MinIO successfully and promoted the `sha-d8f3a38` tags to
   dev. The prod overlay remained on `sha-a3e8669`.
3. Both VM sync destinations were prepared at `~/kube-study/k3s/`. The transfer dry-run
   excluded protected environment/venv paths. New API and worker virtual environments were
   created on each VM with `uv sync --frozen`.
4. The existing dev root Application was switched first. After its eight Applications were
   Synced/Healthy and smoke/observability checks passed, the existing prod root was switched.
   Prod's `album-prod` remains manual-sync; the root's `/operation` ignore rule and
   `RespectIgnoreDifferences` remain in effect.
5. Once both clusters used only the new source paths, the 112 tracked root copies and bridges
   were removed. The cleanup is recorded in commit `2d8e8c4`.

## Live source map

| Application source | dev | prod |
|---|---|---|
| root | `k3s/argocd/bootstrap/dev` | `k3s/argocd/bootstrap/prod` |
| album | `k3s/k8s/gitops/dev/application` | `k3s/k8s/gitops/prod/application` |
| credentials | `k3s/argocd/prerequisites/dev` | `k3s/argocd/prerequisites/prod` |
| observability | `k3s/argocd/observability` | `k3s/argocd/observability` |
| platform | `k3s/k8s/gitops/dev/platform` | `k3s/k8s/gitops/prod/platform` |

The Helm applications use `$values/k3s/infra/keda/values.yaml`,
`$values/k3s/infra/monitoring/values.yaml` plus their environment-specific monitoring file,
and `$values/k3s/infra/sealed-secrets/values.yaml`.

## Verification

- On both VMs, the shared helper suite passed 31 tests, the API suite passed 12 tests, the
  worker suite passed 8 tests, and API/worker Ruff checks passed.
- Argo repo-server uses Kustomize v5.8.1 with no custom build options. All old bridges
  rendered before transition; all new source paths rendered after transition. All 16
  Applications remained Synced/Healthy.
- Dev and prod smoke checks each uploaded a generated image, reached `DONE`, fetched both WebP
  thumbnail sizes and the original bytes, and deleted the QA image. The browser UI also
  completed upload, detail inspection, and confirmed deletion in dev. Captures:
  [uploaded photo details](../../.omo/evidence/k3s-aks-layout/task-6-dev-ui.png),
  [gallery after cleanup](../../.omo/evidence/k3s-aks-layout/task-6-dev-ui-clean.png).
- Each cluster retained all six Bound PVC identities. Their before/after UID fingerprints are
  recorded in [cutover evidence](../../.omo/evidence/k3s-aks-layout/task-4-cutover.txt).
- Observability passed five dashboards, 20 sampled panels, and three required alerts in both
  environments. Prod required a second disposable QA job because KEDA had scaled the worker to
  zero and its processing histogram had no finite sample at the first check.
- On both VMs, `python3 scripts/prepare-release.py --release v0.0.0 --dry-run` selected
  `sha-d8f3a38` for all four components. The prod overlay SHA-256 was unchanged before and
  after; no release alias, tag, or prod deployment was created.
- Nine new Kustomize entrypoints rendered, and 39 Markdown files with 155 local links passed.

## State boundaries and recovery

This was a repository and GitOps source-path migration. It did not copy application data,
move user traffic, delete either K3S environment, or create AKS resources. The prior
completion record for an empty-OS recovery still does not count as a data restore test.
Dev's existing VM-only environment file was preserved with its permissions; prod had no such
file and no credentials were created. SealedSecrets key backups stayed in their existing
external locations and their contents were not read.

The AKS tenant/subscription target still needs owner confirmation. No AKS implementation card
is complete until that target and its access are verified.

The old source paths were deliberately removed after both roots switched. To restore an old
path during recovery, first restore the compatibility files from before cleanup commit
`2d8e8c4`, publish them, and only then change the existing root Application back. Do not point
a live root at a path that is no longer present. For production workload changes, preserve the
manual `album-prod` Sync boundary.
