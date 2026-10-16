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
