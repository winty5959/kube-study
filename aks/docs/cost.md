# AKS cost and minimum capacity

## Current estimate

The selected cluster has two `Standard_D4as_v5` system nodes in Korea Central. The Azure Retail
Prices API snapshot in [A0 evidence](../../.omo/evidence/aks-implementation/A0-preflight-enterprise.txt)
reported `$0.212` per VM-hour for D4as_v5 and `$0.192` for F4s_v2. Over 730 hours, two nodes cost
about `$309.52` and `$280.32`, respectively. The selected D4as_v5 pair is `$29.20/month` more
(`$354.83` vs. `$325.63`) after adding the same `$45.314` estimate for fixed items. The difference
is about 9%. F4s_v2 is a price comparison only: Azure reported it unavailable for this subscription
in the queried regions, including Korea Central.

These are public retail estimates, not the Enterprise agreement invoice. They exclude discounts,
tax, actual storage I/O, traffic, backup, and delayed billing adjustments. An AKS stop removes
node compute charges while stopped; retained disks, public IPs, and other resources can continue
to incur charges. A15 records the actual cost query after Azure billing has had time to post.

## Initial posted ActualCost (partial)

An authenticated Azure Cost Management `ActualCost` query was run at approximately
2026-10-17 03:00 KST for usage date 2026-10-16, separately at the AKS resource-group and node
resource-group scopes. The AKS resource group returned no rows. The node resource group returned
KRW 1,223.91 across the following meter categories:

| Meter category | Posted cost (KRW) | Rows |
|---|---:|---:|
| Virtual Machines | 888.24 | 2 |
| Storage | 147.43 | 12 |
| Load Balancer | 158.63 | 1 |
| Virtual Network | 28.51 | 1 |
| Bandwidth | 1.11 | 1 |
| **Total** | **1,223.91** | **17** |

This is an early partial posting, not the full first-day cost: the query ran while the current UTC
usage date was still in progress and before 24 hours had elapsed from the A11 AKS restart. It is
not a valid direct comparison with the 730-hour retail estimate. The report uses KRW, so no
exchange-rate conversion is included. See the raw sanitized scope, meter totals, and inventory
summary in [A15 cost evidence](../../.omo/evidence/aks-implementation/A15-cost.txt).

At the inventory check, the node resource group contained one current VM scale set at capacity two
and nine managed disks, all attached; no unattached managed disks were listed. Cost rows include
historical resource IDs that are no longer in that current VM scale-set listing. They were not
deleted or treated as unused. A15 remains open until the final release experiments finish and
the posted node, retained-data, network, and temporary-resource charges can be reconciled.
Existing K3S development resource-group costs were queried separately in the AX subscription;
those rows are summarized below.

## Refreshed AKS ActualCost (partial)

An authenticated `ActualCost` / `PreTaxCost` query was run at approximately 2026-10-18 12:55 UTC,
grouped by UTC usage date, resource ID, and meter category. The request covered
2026-10-16T00:00Z through 2026-10-18T00:00Z. Azure returned 52 node-resource-group rows spanning
Oct 16, Oct 17, and partial Oct 18; the AKS resource-group scope returned no rows.

| UTC usage date | Node RG total (KRW) | Rows |
|---|---:|---:|
| 2026-10-16, partial after restart | 6,934.55 | 22 |
| 2026-10-17 | 9,655.21 | 15 |
| 2026-10-18, partial | 2,147.96 | 15 |

The Oct 17 meter categories were Virtual Machines KRW 8,260.29, Storage KRW 712.13,
Load Balancer KRW 574.31, Virtual Network KRW 107.27, and Bandwidth KRW 1.21. Oct 16 and Oct 18
category breakdowns are preserved in [A15 cost evidence](../../.omo/evidence/aks-implementation/A15-cost.txt).
These are posted usage amounts, not invoice-period totals. The Oct 18 row is partial, and the
values must not be compared directly with the USD retail estimate or combined with K3S costs.

At 2026-10-18 13:17 UTC, the cluster was `Stopped` / `Succeeded` to pause node compute charges
while PR #5 awaits review. The ActualCost query above was made before the stop and does not measure
the post-stop period. Retained disks, the public IP, and other resources may continue to incur
charges. Nine disks remain provisioned (33 GiB); the Azure inventory currently reports them
`Unattached` while the nodes are stopped. Query ActualCost again after the release experiments and
allow for billing-posting delay before closing A15.

A repeat ActualCost query at 2026-10-18 13:22 UTC returned the same 52 node-resource-group rows
and the same partial Oct 16–18 totals; the AKS resource group still returned zero rows. No new
usage rows had posted since the prior query. This short-interval result does not measure the
stop's cost impact; retain the 24–48 hour posting wait and repeat after release experiments.

## Existing K3S development environment ActualCost

At 2026-10-17 03:32 KST, a separate Cost Management `ActualCost` / `PreTaxCost` query covered
`rg-seonung-kube-study` in the AX subscription, grouped by UTC usage date, resource ID, and meter.
The resource group total includes the dev/prod VMs, storage, virtual network, and bandwidth; it
must not be added to the AKS subscription as if it were AKS cost.

| UTC usage date | RG total (KRW) | Virtual Machines | Storage | Virtual Network | Bandwidth |
|---|---:|---:|---:|---:|---:|
| 2026-10-14 | 1,737.15 | 1,615.90 | 81.78 | 38.77 | 0.70 |
| 2026-10-15 | 2,323.53 | 1,685.55 | 429.21 | 204.07 | 4.71 |
| 2026-10-16, partial at query time | 676.46 | 312.04 | 246.38 | 116.21 | 1.82 |

The resource-ID rows for `vm-kube-dev` (the existing K3S development VM) show VM and bandwidth
costs of KRW 1,616.59 on Oct 14, KRW 958.78 on Oct 15, and KRW 163.02 on Oct 16 through the
query time. `vm-kube-prod` rows show KRW 731.48 on Oct 15 and KRW 150.85 on Oct 16 through query
time; Azure reported that VM deallocated at the inventory check. These are posted `PreTaxCost`
amounts, not a complete billing-period total. The K3S resource-group totals are separate from
the AKS cost scopes and are not converted to USD. Other AX-subscription resource groups were
excluded from this K3S-specific comparison.

## Current resource inventory

At 2026-10-17 03:32 KST, the AKS resource group contained the cluster, control-plane resource,
and VNet, all provisioning Succeeded. Its node resource group had one two-node D4as_v5 VMSS,
one Standard load balancer, one attached Standard static public IP, and nine Standard SSD LRS
disks totaling 33 GiB. Every disk mapped to a Bound `Retain` PV; no unattached disk or temporary
node pool was found. The AKS dev fixture was clean after smoke, the intentional migrated photo
remained, and the `album-prod` data services and PVCs remain for the gated release exercise.
See [cleanup inventory](cleanup.md) and [A15 evidence](../../.omo/evidence/aks-implementation/A15-cost.txt).

## Capacity evidence

Each D4as_v5 node reports 3860m CPU and approximately 14.49 GiB memory allocatable. During the
500-image workload, both API (3 replicas) and KEDA worker (2 replicas) were active. Node requests
were `2047m / 2972Mi` (53% CPU / 20% memory) and `980m / 1408Mi` (25% CPU / 9% memory), below
the A10 80% request limit. The 200-VU sample reached 85% actual CPU on the busier node and 23%
on the other node; no Pending workload or node pressure was observed in the post-run inspection.

The D4as_v5 pair carried the tested dev workload without a node shortage, repeated OOM, eviction,
or DiskPressure. The peak CPU concentration leaves limited headroom on the busier node, so this
result is specific to the tested workload and scheduler placement. Keep the measured peak in view
when deciding whether production traffic or additional services require a larger pool. Do not
reduce requests or limits solely to improve the percentages.

When the cluster is not in an experiment, use the documented AKS stop/start procedure rather than
deallocating its VM scale set directly. Do not remove Retain disks unless their ownership and
backup/restore evidence have been checked individually.

## Latest ActualCost and inventory snapshot

At 2026-10-18 14:32 UTC, an authenticated ActualCost/PreTaxCost query covered the AKS resource
group and node resource group separately for 2026-10-16 through the partial 2026-10-18 usage date.
The AKS resource group returned zero rows. The node resource group returned 52 KRW rows across 21
resource IDs, totaling KRW 19,547.98 so far. Oct 16 and Oct 18 are partial. The date and meter
totals, query parameters, and resource inventory are in [A15 refresh evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt).

| UTC usage date | Virtual Machines | Storage | Load Balancer | Virtual Network | Bandwidth | Total KRW |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10-16, partial | 5,957.26 | 461.71 | 435.51 | 77.67 | 2.39 | 6,934.55 |
| 2026-10-17 | 8,260.29 | 712.13 | 574.31 | 107.27 | 1.21 | 9,655.21 |
| 2026-10-18, partial | 2,430.35 | 271.82 | 215.36 | 40.23 | 0.47 | 2,958.22 |

The current Retail Prices API response still returns USD 0.212 per D4as_v5 VM-hour. A request for
KRW returned KRW 289.327 per hour using the API's current retail currency conversion. The
two-node 730-hour estimate remains USD 309.52 for compute and USD 354.83 including the existing
fixed-item estimate. The localized KRW rate is not the historical FX or negotiated rate used on
the subscription invoice. These partial posted amounts therefore do not establish a complete
monthly variance; repeat after the release exercises and billing delay.

At 2026-10-18 14:34 UTC, AKS was Running/Succeeded with two D4as_v5 nodes. Nine attached
StandardSSD_LRS disks mapped to nine Bound Retain PVs totaling 33 GiB. The AKS resource group
contains the cluster, control-plane identity, and VNet; the node resource group contains one
two-instance VMSS, one Standard load balancer, and one Standard static public IP. No unowned disk
or cleanup candidate was established. The dev workloads were available; prod application
replicas were zero while PR #6 awaited review.

The AX subscription K3S dev and prod VMs read as deallocated in the 14:34 UTC inventory. Their
managed disks remained present. This project did not change or delete the K3S source. The AKS
cluster stop was requested at 14:38 UTC while A12 review is pending. Azure confirmed `Stopped` /
`Succeeded` at 14:40 UTC. Node compute is paused; retained disks and network resources may still
accrue charges. A15 remains open for final release testing and delayed ActualCost reconciliation.

## Release-window ActualCost and final pause

At 2026-10-18 17:26 UTC (2026-10-19 02:26 KST), an authenticated `ActualCost` / `PreTaxCost`
query covered 2026-10-16T00:00Z through 2026-10-20T00:00Z, grouped daily by resource ID and
meter category. The AKS and node resource groups were queried separately. The AKS resource group
returned zero rows; the node resource group returned 52 KRW rows across 21 resource IDs.

| UTC usage date | Virtual Machines | Storage | Load Balancer | Virtual Network | Bandwidth | Total KRW |
|---|---:|---:|---:|---:|---:|---:|
| 2026-10-16, partial | 5,957.256181 | 461.714050 | 435.512096 | 77.672197 | 2.393719 | 6,934.548243 |
| 2026-10-17 | 8,260.287702 | 712.129790 | 574.310265 | 107.269350 | 1.212985 | 9,655.210093 |
| 2026-10-18, partial | 3,124.731600 | 334.592866 | 263.114152 | 49.165119 | 0.564561 | 3,772.168299 |
| **Reported total** | **17,342.275483** | **1,508.436706** | **1,272.936513** | **234.106666** | **4.171265** | **20,361.926634** |

The query was unchanged from 17:08 UTC. No row yet covered the AKS restart at 17:11:29 UTC or
the release and stop work through 17:30:59 UTC. This short ActualCost period does not measure
those charges or demonstrate savings. Dates include two partial days and are in KRW; the USD
354.83/month retail estimate is not a direct comparison with this posted total. Do not infer
invoice FX or a final monthly variance.

Azure confirmed `Stopped` / `Succeeded` at 17:30:59 UTC. The node VMSS has capacity zero and no
instances. Nine StandardSSD_LRS disks are `Unattached`, having mapped immediately before stop to
nine Bound Retain PVCs totaling 33 GiB. The Standard load balancer and static Standard public IP
remain provisioned and may continue to incur charges. No resource was deleted. See [latest A15
evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt).

A15 stays open until ActualCost has had the plan's 24–48 hours to post the restart/release/stop
usage. The earliest recheck is after 2026-10-19 17:31 UTC; use a later query if the new usage date
has not appeared. Then reconcile VM, OS disk, PVC, load balancer, IP, I/O, egress, and any backup
meters against the retail estimate without combining the AX K3S scope.
