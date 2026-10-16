# AKS-NODE: drain and LRS volume reattachment

## Baseline

- `album-dev` held one restored `DONE` photo, 1,064 bytes. The original download SHA-256 was
  recorded before drain; it matched after drain.
- The API PDB required one available replica. We temporarily raised the API HPA minimum from one
  to two, waited for both API pods to be Ready, and confirmed one disruption was allowed.
- Frontend stayed at two replicas with one disruption allowed. PostgreSQL, Redis, and MinIO were
  each one replica on the other node. Their three LRS PVCs were Bound with `Retain` policy.
- The destination node had 680m CPU requests (17%) and 1Gi memory requests (6%) before the drain.
  Moving the data and platform pods kept it below 80% requests during the experiment.

## Drain

Paused `root-dev` and `album-dev` automated sync to hold the temporary HPA setting. At
2026-10-16T16:17:38Z, drained the node that held the three data pods with
`kubectl drain --ignore-daemonsets --delete-emptydir-data --timeout=10m`; no `--force` was used.
PDBs delayed metrics-server and CoreDNS eviction until replacement pods were Ready. The drain then
completed. PostgreSQL, Redis, and MinIO briefly waited for the old RWO disk attachment to detach;
CSI attached each disk to the remaining node, and all three Pods returned Ready. The detach/attach
wait was approximately 20 seconds; the services were Ready within about 40 seconds.

With the node still drained, API readiness reported Postgres, Redis, and S3 healthy. The generated
upload reached DONE, both WebP thumbnails had the expected 200x100 and 800x400 sizes, original
download returned 3,462 bytes, and delete returned 204. The restored photo remained the only DB
row and its original checksum still matched the pre-drain value. The drained node was uncordoned;
API HPA minimum one and both Argo automated sync policies were restored. Argo returned to
Synced/Healthy.

The source K3S cluster and its data were not changed.
