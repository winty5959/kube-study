# AKS acceptance and completion status

**Status: in progress, not complete.** The repository migration, AKS foundation, dev workload,
recovery exercises, and A14 dev-only cutover rehearsal have evidence. Release promotion and the
final delayed-cost reconciliation remain open.

## Acceptance ledger

| Plan card | Current status | Evidence / remaining work |
|---|---|---|
| K3S path migration, tasks 1–6 and F1–F4 | Complete | [Migration plan](../../.omo/plans/k3s-onprem-aks-migration.md) |
| A0–A11 AKS foundation, workload, recovery and operations | Complete | [Implementation plan](../../.omo/plans/aks-implementation.md) and `.omo/evidence/aks-implementation/` |
| A12 release promotion | In progress; smoke failed | [PR #4](https://github.com/winty5959/kube-study/pull/4) merged. `platform-prod` and `album-prod` are Synced/Healthy at the merge SHA, but the PostSync smoke failed because thumbnail URLs returned frontend HTML. [PR #5](https://github.com/winty5959/kube-study/pull/5) adds the Traefik class and patches the frontend scan finding; after merge, publish a new immutable release alias and rerun prod smoke. |
| A13 AKS experiments | Partial | E-01–E-12 and E-15 pass. E-13 promotion and E-14 rollback wait for A12 to pass with the corrected release. See [experiment results](experiments/README.md). |
| A14 dev cutover rehearsal | Complete | [A14 evidence](../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt) |
| A15 costs, final status and cleanup | In progress | [A15 cost evidence](../../.omo/evidence/aks-implementation/A15-cost.txt). A repeat ActualCost query now returns Oct 16–18 rows; Oct 18 is partial and the totals still need final reconciliation after release experiments. A separate query covers the existing K3S dev/prod resource group. No Azure resource or PVC was deleted. |

## Current Azure state

As of 2026-10-18 13:17 UTC, `aks-kube-study` is `Stopped` with provisioning `Succeeded` in
`Enterprise부문-아키텍처강화TF` / `rg-seonung-aks-test`, Korea Central. The configured system pool
still has two `Standard_D4as_v5` nodes. Before stopping, the dev API, frontend, and worker and the
same three prod workloads were scaled to zero; API HPAs were removed. `root-dev` and `album-dev`
automated sync were paused so Argo CD cannot restart workloads while AKS is stopped. The one
migrated dev photo remained `DONE`, prod had zero photo rows, and both namespaces' Redis queues
were empty. Prod's previous `album-prod` sync at merge SHA
`51b9ea9f3285866b26cfe4daa5db70b40a6c31d7` had failed because the PostSync thumbnail smoke
received HTTP 200 with `text/html` instead of `image/webp`; its generated fixture was deleted
through the API (204; follow-up GET 404). No new prod sync was run before stopping. Full A12
verification remains open.

The latest ActualCost query returned node-resource-group totals of KRW 6,934.55 for Oct 16,
KRW 9,655.21 for Oct 17, and KRW 2,147.96 for partial Oct 18; the AKS resource group returned no
rows. This query predates the stop. Reconcile posted costs after E-13/E-14 and query again after
the release work before closing A15. While AKS is stopped, node compute charges pause; retained
disks, public IP, and other resources may still incur charges. Nine managed disks currently report
`Unattached` because the nodes are stopped; the pre-stop inventory mapped them to nine Bound
Retain PVCs. See [cleanup inventory](cleanup.md) and the [temporary stop record](experiments/AKS-STOP.md).
Restart and verify data recovery before resuming experiments.

## Project boundary

This project does not switch real K3S user traffic, alter production DNS, or delete the K3S
source. A14 exercised only a local AKS test route. Any live cutover or source retirement remains
a separate decision.
