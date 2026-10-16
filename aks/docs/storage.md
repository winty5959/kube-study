# AKS storage

`album-standard-ssd-retain` is the AKS-owned StorageClass for application and monitoring claims.
It uses Azure Disk CSI (`disk.csi.azure.com`), `StandardSSD_LRS`, ext4, `WaitForFirstConsumer`,
volume expansion, and `Retain`. AKS's built-in StorageClasses remain untouched. The dev platform
Kustomize application includes this cluster-scoped class so a future ArgoCD bootstrap adopts the
same object.

PostgreSQL requests 2Gi, Redis 1Gi, MinIO 10Gi, Prometheus 5Gi, Grafana 1Gi, and Alertmanager 1Gi.
The sum requested is 20Gi. Azure bills Standard SSD by disk tier, so the planning estimate counts
40Gi across the six claims; verify the actual tier and price after application PVCs are provisioned.

## Provisioning probe

On 2026-10-16, a temporary 5Gi claim using the production StorageClass bound after its consumer Pod
was scheduled. Azure created a 5Gi `StandardSSD_LRS` managed disk. A non-root container wrote
`azure-disk-persistence-ok`, its Pod was deleted and recreated, and the same content was read after
reattachment. The test claim, Pod, PV, and retained managed disk were then removed; no probe disk
remains. This validates CSI provisioning and reattachment, not the PostgreSQL, Redis, MinIO, or
Prometheus application containers, which are tested in A6/A8.

`Retain` preserves a disk when its claim is deleted; it is not a backup and the disk continues to
cost money. Before retiring a claim, identify its retained PV and decide whether to back up, rebind,
or explicitly delete the disk. Never change a live StatefulSet claim's StorageClass in place. For
class changes, create a replacement claim, copy/restore data, verify the application, then switch.
An unbound claim can remain Pending until a Pod consumes it because volume binding waits for a
consumer; this is expected.

The test disk's request was only 5Gi, so this probe does not establish the billed tier for every
planned claim size. Reconcile the six production disks with the cost table after A6 creates them.
