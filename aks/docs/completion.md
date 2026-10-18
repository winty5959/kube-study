# AKS acceptance and completion status

**Status: in progress, not complete.** The repository migration, AKS foundation, dev workload,
recovery exercises, and A14 dev-only cutover rehearsal have evidence. Release promotion and the
final delayed-cost reconciliation remain open.

## Acceptance ledger

| Plan card | Current status | Evidence / remaining work |
|---|---|---|
| K3S path migration, tasks 1–6 and F1–F4 | Complete | [Migration plan](../../.omo/plans/k3s-onprem-aks-migration.md) |
| A0–A11 AKS foundation, workload, recovery and operations | Complete | [Implementation plan](../../.omo/plans/aks-implementation.md) and `.omo/evidence/aks-implementation/` |
| A12 release promotion | In progress; manual release test pending | PRs #4 and #5 are merged. [PR #6](https://github.com/winty5959/kube-study/pull/6) proposes aks-v1.0.1. Its four immutable GHCR alias digests match the current dev digests, but it has no owner review or reported PR checks. Prod application Sync and smoke have not been rerun after this release candidate. [Current A12 evidence](../../.omo/evidence/aks-implementation/A12-current-release.txt). |
| A13 AKS experiments | Partial | E-01–E-12 and E-15 pass. E-13 promotion and E-14 rollback wait for A12 to pass with the reviewed release. See [experiment results](experiments/README.md). |
| A14 dev cutover rehearsal | Complete | [A14 evidence](../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt) |
| A15 costs, final status and cleanup | In progress | [A15 cost evidence](../../.omo/evidence/aks-implementation/A15-cost.txt) and [latest refresh](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt). Oct 18 remains partial and the final variance requires post-release usage and billing posting. No Azure resource or PVC was deleted. |

## Current Azure state

Before the temporary stop, at 2026-10-18 14:34 UTC, `aks-kube-study` was Running/Succeeded in
`Enterprise부문-아키텍처강화TF` / `rg-seonung-aks-test`, Korea Central, with two Ready
`Standard_D4as_v5` nodes. Dev API is 1/1, frontend 2/2, and worker 0/0; the [browser evidence](../../.omo/evidence/aks-implementation/A8-browser-resumed.txt)
records the existing photo card and loaded thumbnail and detail image. Prod API, frontend, and worker
remain at zero replicas. Prod PostgreSQL, Redis, and MinIO are Ready, and all nine PVCs remain
Bound with Retain policy.

PR #6 remains unmerged and has no owner review or reported PR checks. The four aks-v1.0.1 image
aliases match the current dev manifest digests. `root-prod` is Synced at current main;
`platform-prod` and `album-prod` remain manually synced and OutOfSync. The last album-prod
PostSync smoke operation is still Failed from the earlier thumbnail route issue. This turn did
not run a prod Sync. A12 requires owner review/merge, manual application Sync, a passing prod
smoke, and running digest comparison.

The latest authenticated ActualCost query (2026-10-18 14:32 UTC) returned zero rows for the AKS
resource group and 52 KRW rows totaling KRW 19,547.98 in the node resource group across partial
Oct 16, full Oct 17, and partial Oct 18. The public retail estimate remains USD 354.83/month; the actual rows are partial and
in KRW, so final reconciliation waits for A12/A13 and billing posting. See [cost](cost.md),
[cleanup inventory](cleanup.md), and [A15 refresh evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt).

At 2026-10-18 14:38 UTC, a stop was requested while the release review is pending. Azure confirmed
`powerState=Stopped`, `provisioningState=Succeeded` at 14:40 UTC. Node compute is paused; retained
disks and network resources may continue to incur charges.

The existing AX subscription K3S dev and prod VMs read as deallocated at 14:34 UTC. Their managed
disks remain present. This project did not change or delete source resources, and no user traffic
was redirected to AKS. A14 remains a historical dev-only rehearsal; it does not prove current K3S
service availability.

## Project boundary

This project does not switch real K3S user traffic, alter production DNS, or delete the K3S
source. A14 exercised only a local AKS test route. Any live cutover or source retirement remains
a separate decision.
