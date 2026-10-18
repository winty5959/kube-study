# AKS resource inventory and cleanup

## Inventory snapshot

Checked 2026-10-18 22:02 KST in the selected Enterprise subscription. The AKS cluster is
Running, provisioning succeeded, and the single system VM scale set has capacity two at
`Standard_D4as_v5`.

| Scope | Current resources | State |
|---|---|---|
| `rg-seonung-aks-test` | AKS cluster, control-plane resource, VNet | All provisioning Succeeded |
| `MC_rg-seonung-aks-test_aks-kube-study_koreacentral` | One two-node VM scale set, one Standard load balancer, one attached Standard static public IP, node security/network resources | Provisioning Succeeded |
| AKS node resource group | Nine `StandardSSD_LRS` managed disks, total 33 GiB | All Attached to the two current VMSS instances |

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

The AKS cluster remains Running for the approved release and experiment work. For an intentional
pause, use the checked [stop/start procedure](operations.md#stop-and-start) and
[power evidence](experiments/AKS-STOP.md); do not deallocate the VM scale set or delete Retain
disks. Refresh this inventory and actual costs before a later cleanup decision.
