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
deleted or treated as unused. A15 remains open until at least 24-48 hours of usage has posted and
the retained data, node, and temporary-resource charges can be reconciled. Existing K3S
development resource-group costs were queried separately in the AX subscription; those rows are
summarized below.

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
