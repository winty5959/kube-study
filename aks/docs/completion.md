# AKS acceptance and completion status

**Status: in progress, not complete.** The repository migration, AKS foundation, dev workload,
recovery exercises, and A14 dev-only cutover rehearsal have evidence. Release promotion and the
final delayed-cost reconciliation remain open.

## Acceptance ledger

| Plan card | Current status | Evidence / remaining work |
|---|---|---|
| K3S path migration, tasks 1–6 and F1–F4 | Complete | [Migration plan](../../.omo/plans/k3s-onprem-aks-migration.md) |
| A0–A11 AKS foundation, workload, recovery and operations | Complete | [Implementation plan](../../.omo/plans/aks-implementation.md) and `.omo/evidence/aks-implementation/` |
| A12 release promotion | Waiting for user review and approval | [PR #4](https://github.com/winty5959/kube-study/pull/4) is open. `root-prod` and `platform-prod` are manually synced; `album-prod` remains Missing. Do not sync it before the approved release merge. |
| A13 AKS experiments | Partial | E-01–E-12 and E-15 pass. E-13 waits on A12; E-14 has not run. See [experiment results](experiments/README.md). |
| A14 dev cutover rehearsal | Complete | [A14 evidence](../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt) |
| A15 costs, final status and cleanup | In progress | [A15 cost evidence](../../.omo/evidence/aks-implementation/A15-cost.txt). The AKS ActualCost query is still an early partial posting; repeat after 24–48 hours of usage have posted. A separate ActualCost query now includes the existing K3S dev and prod VM resource group. No resource was deleted. |

## Current Azure state

As of 2026-10-17 03:32 KST, `aks-kube-study` is Running in
`Enterprise부문-아키텍처강화TF` / `rg-seonung-aks-test`, Korea Central, with two
`Standard_D4as_v5` nodes. The dev API and two frontends are Ready, the worker is idle at zero,
and the migrated dev fixture remains one `DONE` row. Its Redis queues are empty. The platform
StatefulSets and three Retain PVCs in `album-prod` are Ready/Bound for the pending release
exercise; the `album-prod` application itself remains manually managed and Missing.

The latest ActualCost data does not cover a full AKS day after the 2026-10-16 16:34 UTC restart.
The AKS cluster is still Running, so compute usage continues. Current storage, networking, and
resource attachment details are in [cleanup inventory](cleanup.md).

## Project boundary

This project does not switch real K3S user traffic, alter production DNS, or delete the K3S
source. A14 exercised only a local AKS test route. Any live cutover or source retirement remains
a separate decision.
