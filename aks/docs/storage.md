# AKS storage

`album-standard-ssd-retain` is the AKS-owned StorageClass for application and monitoring claims.
It uses Azure Disk CSI (`disk.csi.azure.com`), `StandardSSD_LRS`, ext4, `WaitForFirstConsumer`,
volume expansion, and `Retain`. AKS's built-in StorageClasses remain untouched. The dev platform
Kustomize application includes this cluster-scoped class so a future ArgoCD bootstrap adopts the
same object.

PostgreSQL requests 2Gi, Redis 1Gi, MinIO 10Gi, Prometheus 5Gi, Grafana 1Gi, and Alertmanager 1Gi.
The sum requested is 20Gi. On 2026-10-16, all six PVCs bound to Azure managed disks using
`StandardSSD_LRS`; Azure charges by disk tier, so the public-price estimate remains 40Gi of E1/E2/E3
billable tiers across these claims. The six retained disks are present and continue to accrue storage
charges while the cluster is running or stopped.

## Provisioning probe

On 2026-10-16, a temporary 5Gi claim using the production StorageClass bound after its consumer Pod
was scheduled. Azure created a 5Gi `StandardSSD_LRS` managed disk. A non-root container wrote
`azure-disk-persistence-ok`, its Pod was deleted and recreated, and the same content was read after
reattachment. The test claim, Pod, PV, and retained managed disk were then removed; no probe disk
remains. This validates CSI provisioning and reattachment. A6 confirms that PostgreSQL, Redis,
MinIO, Prometheus, Grafana, and Alertmanager reach Ready with their bound claims. A8/A9 validate
the photo workflow and restored application data.

`Retain` preserves a disk when its claim is deleted; it is not a backup and the disk continues to
cost money. Before retiring a claim, identify its retained PV and decide whether to back up, rebind,
or explicitly delete the disk. Never change a live StatefulSet claim's StorageClass in place. For
class changes, create a replacement claim, copy/restore data, verify the application, then switch.
An unbound claim can remain Pending until a Pod consumes it because volume binding waits for a
consumer; this is expected.

A4 established CSI behavior; A6 established the actual six managed disks and storage SKU. The
remaining cost estimate uses the repository's public Azure disk tier prices, not invoice data.
