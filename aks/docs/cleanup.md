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
before stopping. After the release PR is reviewed and merged, use the checked
[stop/start procedure](operations.md#stop-and-start), restart AKS, verify PVC/data recovery, and
restore dev automation and workload state before further experiments. Keep prod manual pending
the corrected A12 release. Refresh this inventory and posted costs before a later cleanup decision.

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
and [cost reconciliation](cost.md). Repeat the query after release exercises and posting delay.

At 2026-10-18 14:40 UTC, a stop requested while waiting for owner review of PR #6 reached
`powerState=Stopped` and `provisioningState=Succeeded`. The pre-stop disk-to-PV/PVC mapping remains the
ownership record. A post-stop inventory found zero VMSS instances and all nine disks `Unattached`;
those disks mapped to nine Bound Retain PVs immediately before the stop. This is the expected
stopped-node state, not an orphan finding. Node compute is paused; retained disks, load balancer,
public IP, and network resources may still incur charges.
