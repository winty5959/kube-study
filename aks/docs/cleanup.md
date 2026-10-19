# AKS resource inventory and cleanup

## Inventory snapshot

Historical snapshot checked 2026-10-18 13:22 UTC in the selected Enterprise subscription. The AKS cluster was
`Stopped`, provisioning succeeded, and the system pool is configured for two
`Standard_D4as_v5` nodes. Node compute is paused until the cluster is started again.

| Scope | Current resources | State |
|---|---|---|
| `rg-seonung-aks-test` | AKS cluster, control-plane resource, VNet | All provisioning Succeeded |
| `MC_rg-seonung-aks-test_aks-kube-study_koreacentral` | One system VM scale set configured for two nodes, one Standard load balancer, one Standard static public IP, node security/network resources | AKS is Stopped; provisioning Succeeded |
| AKS node resource group | Nine `StandardSSD_LRS` managed disks, total 33 GiB | All nine currently report `Unattached` while AKS nodes are stopped |

The disk inventory is four 1-GiB disks, two 2-GiB disks, one 5-GiB disk, and two 10-GiB disks.
All nine map by disk ID to Kubernetes PVs with `Retain` policy and Bound PVCs:

| Namespace | Bound PVCs | Requested capacity |
|---|---:|---:|
| `album-dev` | MinIO 1, PostgreSQL 1, Redis 1 | 13 GiB |
| `album-prod` | MinIO 1, PostgreSQL 1, Redis 1 | 13 GiB |
| `monitoring` | Grafana 1, Alertmanager 1, Prometheus 1 | 7 GiB |
| **Total** | **9** | **33 GiB** |

The A14 generated AKS smoke fixture was deleted and its API lookup returned 404. The intentional
migrated dev photo remains `DONE`; `album-dev` queues are empty. Prod data services and their
Bound PVCs remain in place for A12/A13. PR #4 was merged and `album-prod` was manually synced.
Its generated A12 smoke photo was deleted (API 204, then GET 404); both prod Redis queues are
empty. The smoke Job remains Failed pending a route fix and a corrected release; no Azure resource
or PVC was deleted.

## Cleanup decision

No unattached managed disk or temporary node pool was present at the inventory check. Every
managed disk mapped to a `Retain` PV and an existing Bound PVC, so there is no verified disk
candidate for removal. The main AKS resource group, load balancer, public IP, VM scale set, and
data disks are in use. Historical cost rows alone do not establish that a resource is unused.
No Azure resource or PVC was deleted.

The nine PVCs were Bound to `Retain` PVs at the pre-stop check; Azure reported all nine disks
`Unattached` after the cluster stop. This is the expected stopped-node state, not evidence that
they are orphaned or safe to delete. No PVC, disk, or other Azure resource was deleted. The dev
application replicas were scaled to zero, API HPAs removed, and dev Argo automated sync paused
before stopping. PR #6 was merged and E-13/E-14 completed before the final stop. For later work,
use the checked [stop/start procedure](operations.md#stop-and-start), restart AKS, verify PVC/data
recovery, and restore dev automation and workload state. Keep prod manual. Refresh this inventory
and posted costs before a later cleanup decision.

## Refreshed inventory

Checked 2026-10-18 14:34 UTC in the selected Enterprise subscription. AKS was Running/Succeeded
with two Ready Standard_D4as_v5 nodes. The AKS resource group contains the cluster, control-plane
managed identity, and VNet, all provisioning Succeeded. The node resource group contains one
two-instance VM scale set, one Standard load balancer, one Standard static public IP, and nine
attached StandardSSD_LRS disks. All nine disk IDs map to Bound Retain PVs; Kubernetes reports
33 GiB requested across album-dev, album-prod, and monitoring.

The prod API, frontend, and worker deployments are at zero replicas while the release PR awaits
owner review. Prod PostgreSQL, Redis, and MinIO remain Ready. No unattached AKS disk, unowned PV,
or temporary node pool was found. No Azure or Kubernetes resource was deleted.

The source AX subscription K3S dev and prod VMs were both deallocated at this read-only check.
Three managed disks remain in the source resource group (two Reserved and one Unattached). This
task did not alter or delete them; no cleanup candidate was inferred from the VM power state.
Their current service availability is not proven by the earlier A14 rehearsal.

The latest posted ActualCost snapshot is partial: the AKS resource group returned no rows and the
node resource group returned 52 KRW rows through partial Oct 18. See [A15 refresh evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt)
and [cost status](cost.md). At the time, a later query was planned; the user's final cost-skip instruction is recorded below.

At 2026-10-18 14:40 UTC, a stop requested while waiting for owner review of PR #6 reached
`powerState=Stopped` and `provisioningState=Succeeded`. The pre-stop disk-to-PV/PVC mapping remains the
ownership record. A post-stop inventory found zero VMSS instances and all nine disks `Unattached`;
those disks mapped to nine Bound Retain PVs immediately before the stop. This is the expected
stopped-node state, not an orphan finding. Node compute is paused; retained disks, load balancer,
public IP, and network resources may still incur charges.

## Release-exercise inventory, 2026-10-18 17:31 UTC

The owner-merged `aks-v1.0.1` release and E-13/E-14 completed before the final stop. The stop
helper finished successfully at 17:30:59 UTC and Azure reported `Stopped` / `Succeeded`.

| Scope | Observed state |
|---|---|
| `rg-seonung-aks-test` | AKS cluster, control-plane identity, and VNet remain provisioned |
| `MC_rg-seonung-aks-test_aks-kube-study_koreacentral` VMSS | One `Standard_D4as_v5` system pool configured for two; VMSS capacity zero and no instances |
| Node resource group load balancer | One Standard load balancer, provisioning Succeeded |
| Node resource group public IP | One Standard static public IP, provisioning Succeeded |
| Managed disks | Nine StandardSSD_LRS disks, all `Unattached` after stop |

Immediately before stop, Kubernetes showed nine Bound Retain PVCs requesting 33 GiB: 13 GiB in
`album-dev`, 13 GiB in `album-prod`, and 7 GiB in `monitoring`. Azure disk IDs mapped to those
PVs. The disks becoming Unattached is expected with stopped nodes and is not an orphan signal.
No disk, PVC, Azure resource, or K3S resource was deleted.

At shutdown, dev retained its single intentional `DONE` photo and prod contained zero rows after
the release smoke fixture was deleted. Both Redis job lists were empty and no Job was active. App
Deployments were zero, API HPAs were removed, dev root/app automated sync was paused, and prod
sync remained manual. On next start, restore dev policy and workloads per
[operations](operations.md#stop-and-start); for prod, restore two API replicas and wait for valid
HPA metrics before manual sync.

The preliminary ActualCost query at 17:48 UTC returned 52 node resource group rows totaling KRW
20,640.730839 and zero AKS resource group rows. The partial Oct 18 amount increased by KRW
278.804205 from the 17:26 UTC query, but daily grouping cannot attribute it to exact minutes or
prove that the entire 17:11–17:31 UTC restart/release/stop period has posted. At that time, a repeat
after the 24–48 hour posting delay was planned before final cost reconciliation or a deletion decision. The AKS
inventory does not identify an unused disk or temporary pool eligible for cleanup.

The AX source check showed both `vm-kube-dev` and `vm-kube-prod` present and deallocated. All
three source managed disks remain present (two Reserved, one Unattached). No source resource was
changed and current K3S service availability is not established by this inventory.

## Preliminary post-stop recheck, 2026-10-18 about 17:50 UTC

Read-only Azure CLI queries reconfirmed the AKS system VMSS at capacity zero with no instances,
nine StandardSSD_LRS disks all `Unattached`, one Standard load balancer, and one Standard static
public IP. The nine disk names match the PVC-derived managed disks mapped to Bound Retain PVs just
before stop (33 GiB requested). The cluster remains `Stopped` / `Succeeded`; no resource was
deleted. Cost results from the 17:48 UTC query are preliminary; see [cost reconciliation](cost.md).

## Final delayed-cost wait check, 2026-10-18 18:19 UTC

Resource inventory around 18:16 UTC showed `aks-kube-study` `Stopped` / `Succeeded`, its
`Standard_D4as_v5` system VMSS at capacity zero with no instances, all nine PVC-named
StandardSSD_LRS disks `Unattached`, one Standard load balancer, and one Standard static IP. A
cluster-state query at 18:19 UTC reconfirmed `Stopped` / `Succeeded`. The AX K3S dev/prod VMs were
still deallocated and all three source disks remained present (two Reserved and one Unattached).
No resource was changed or deleted.

The separate daily ActualCost query at 18:18 UTC covered 2026-10-16T00:00Z through
2026-10-21T00:00Z and grouped by ResourceId and MeterCategory. The AKS RG returned zero rows; the
node RG returned 52 KRW rows across 21 resource IDs totaling KRW 20,640.730839: partial Oct 16
KRW 6,934.548243, Oct 17 KRW 9,655.210093, and partial Oct 18 KRW 4,050.972503. These results
were unchanged from 18:10 UTC and were captured before 24 hours had elapsed from the 17:30:59.575028
UTC stop success event. At that time they could not close A15 or prove exact release-window
attribution, and a later query was planned. The user subsequently directed that cost calculation be
skipped; see the final disposition below. Keep the retained disks and other resources until a
separate cleanup decision.

## Final A15 disposition

On 2026-10-19 the user directed that cost calculation be skipped. No further ActualCost query or
cost arithmetic was performed. The latest recorded 18:27 UTC snapshot remains preliminary and is
not a final invoice or an estimate variance. A read-only Azure check at 00:23 UTC confirmed AKS
`Stopped` / `Succeeded`, VMSS capacity zero with no instances, nine PVC-derived StandardSSD_LRS
disks `Unattached`, one Standard load balancer, and one Standard static public IP. A 06:17 UTC
read-only Azure disk tag query mapped each disk ID to its PV name and exact PVC namespace/name.
Immediately before stop, Kubernetes reported the nine claims Bound to Retain PVs; live Kubernetes
bindings are not claimed while stopped. See the [per-disk A15 evidence](../../.omo/evidence/aks-implementation/A15-cost.txt#per-disk-pvc-ownership-evidence-2026-10-19-0617-utc).
No Azure or K3S resource was deleted.
