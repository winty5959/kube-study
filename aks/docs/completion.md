# AKS acceptance and completion status

**Status: in progress, not complete.** The repository migration, AKS foundation, dev workload,
recovery exercises, and A14 dev-only cutover rehearsal have evidence. Release promotion and the
final delayed-cost reconciliation remain open.

## Acceptance ledger

| Plan card | Current status | Evidence / remaining work |
|---|---|---|
| K3S path migration, tasks 1–6 and F1–F4 | Complete | [Migration plan](../../.omo/plans/k3s-onprem-aks-migration.md) |
| A0–A11 AKS foundation, workload, recovery and operations | Complete | [Implementation plan](../../.omo/plans/aks-implementation.md) and `.omo/evidence/aks-implementation/` |
| A12 release promotion | Complete | Owner merged [PR #6](https://github.com/winty5959/kube-study/pull/6). `platform-prod` and `album-prod` were manually synced; migration, PostSync upload/thumbnail/download/delete smoke, runtime digest comparison, and browser Album check passed. GitHub reported no separate review or PR checks. [Current A12 evidence](../../.omo/evidence/aks-implementation/A12-current-release.txt). |
| A13 AKS experiments | Complete | E-01–E-15 are recorded; E-13 promotion and E-14 live rollback/manual Git reconciliation passed after A12. [Experiment results](experiments/README.md) and [A13 evidence](../../.omo/evidence/aks-implementation/A13-experiments.txt). |
| A14 dev cutover rehearsal | Complete | [A14 evidence](../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt) |
| A15 costs, final status and cleanup | In progress; delayed billing pending | Preliminary 17:48 UTC query returned KRW 20,640.730839 across partial Oct 16, Oct 17, and partial Oct 18; the Oct 18 amount increased by KRW 278.804205 since 17:26. Daily grouping cannot prove exact interval attribution. Repeat after the 24-hour posting delay before final reconciliation with the USD 354.83/month retail estimate. Inventory is reconciled; no cleanup candidate or deletion was authorized. [A15 evidence](../../.omo/evidence/aks-implementation/A15-cost.txt) and [latest refresh](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt). |

## Current Azure state

Read-only Azure inventory was rechecked immediately after the preliminary cost query at about
2026-10-18 17:50 UTC. `aks-kube-study` is `Stopped` / `Succeeded` in
`Enterprise부문-아키텍처강화TF` / `rg-seonung-aks-test`. The `Standard_D4as_v5` system pool remains
configured for two nodes; the node VMSS has capacity zero and no instances. A Standard load
balancer, Standard static public IP, and nine StandardSSD_LRS disks remain. All nine disks are
`Unattached` after stop and mapped immediately before stop to nine Bound Retain PVCs requesting
33 GiB total. No disk, PVC, or Azure resource was deleted.

PR #6 was merged by the repository owner at 2026-10-18 17:07:47 UTC. GitHub returned no formal
review record or PR status checks. `root-prod`, `platform-prod`, and `album-prod` are Synced at
merge SHA `1b7e521becccb6117d578d3a1f06132684631f5a`; production automated sync remains disabled.
The release smoke passed and the four running `imageID` digests matched the verified aliases.
The browser screenshot shows the prod Album empty state after fixture cleanup.

Before final stop, dev had its one intentional `DONE` photo and prod had zero photos; no jobs were
active and both namespaces' Redis lists were empty. Dev app automated sync is paused, prod remains
manual, all app deployments are zero, and API HPAs are removed. The existing AX K3S dev and prod
VMs remain deallocated and all three source disks remain present. No K3S resource or real user
traffic was changed. A14 remains a dev-only cutover rehearsal; it does not prove current K3S
service availability.

The preliminary ActualCost query (2026-10-18 17:48 UTC) returned zero AKS resource-group rows and
52 node resource-group rows totaling KRW 20,640.730839 across partial Oct 16, Oct 17, and partial
Oct 18. The Oct 18 total increased by KRW 278.804205 versus 17:26 UTC, including KRW 173.596200
in Virtual Machines. Daily grouping cannot establish exact usage timestamps or prove the entire
17:11–17:31 UTC window is posted. The USD 354.83/month public retail estimate is not an invoice
total. A15 and overall goal completion remain open until a query after the posting delay captures
and reconciles the interval; see
[cost](cost.md), [cleanup inventory](cleanup.md), and [A15 refresh evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt).

## Project boundary

This project does not switch real K3S user traffic, alter production DNS, or delete the K3S
source. A14 exercised only a local AKS test route. Any live cutover or source retirement remains
a separate decision.
