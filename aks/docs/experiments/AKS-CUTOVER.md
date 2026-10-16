# AKS cutover rehearsal

## Boundary

This runbook covers a dev-only rehearsal using the existing K3S dev source and
AKS dev target. It does not switch real user traffic, change DNS, add a public
IP, modify K3S prod, or delete the source environment. Use a generated test
photo for the target write and remove it before restoring source writes.

The 2026-10-16 A9 copy was taken while K3S dev remained online. It is a useful
restore rehearsal but is not a consistent final cutover snapshot. A final
source/target comparison requires a verified source access path, an observed
write freeze, both Redis queues drained, and all `PROCESSING` rows resolved.

## Current rehearsal status

**Partial; source-side freeze and final snapshot were not performed.** The
configured K3S dev kube context could not reach its local API endpoint. The
documented `k3s/scripts/tunnel.sh dev start` attempt timed out while connecting
to the K3S dev VM on SSH. The tunnel status check found no active control
socket. No K3S VM, workload, traffic route, database, queue, or object was
changed. See [A14 evidence](../../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt).

AKS dev was already exercised through the loopback Traefik route
`http://127.0.0.1:18080` with `Host: album.aks.localhost`; the E10 generated
smoke reached `DONE`, and the fixture was deleted. This validates the AKS
endpoint in isolation. It does not prove that a client route was switched from
K3S to AKS or rolled back.

## Rehearsal procedure

1. Open the documented K3S dev SSH tunnel and verify `k3s-dev`, the album app,
   the source PostgreSQL, object store, and both Redis queues. If the source
   cannot be reached, stop here; do not infer it is empty or stopped.
2. Record source row/status/byte counts, object keys/sizes/SHA-256 values, both
   queues, image/schema version, and a verified restore baseline. Schedule and
   record the short write-freeze window before pausing the dev API, worker,
   cleanup, HPA/KEDA, and GitOps paths that can create or process writes.
3. Confirm no request or job can write, both queues are empty, and there are no
   `PROCESSING` rows. Capture a new database dump and object manifest, then
   verify each copied body by size and SHA-256. Keep all payloads outside Git.
4. Pause AKS dev writes and cleanup. Restore the validated snapshot to the AKS
   dev database and object buckets without replacing PVCs. Compare row state,
   object keys, bytes, checksums, schema version, and queues before resuming
   the AKS API and worker.
5. Select the AKS dev URL only in the test client's local base URL/port-forward.
   Keep public DNS and source routes unchanged. Run a generated upload, wait
   for `DONE`, read the original and both thumbnails, then delete the generated
   photo and verify `404`.
6. Stop AKS test writes, verify its test fixture and queues are clean, and
   restore the client's previous K3S dev URL. Resume K3S dev writes only after
   confirming the source still has its recorded baseline. Restore paused
   policies and workloads on both environments and verify health.
7. Record the exact point at which the source is writable again. If any
   destination write remains, do not claim lossless rollback to the source;
   reconcile that delta from a verified backup before reopening source writes.

## Abort conditions

Do not route the client to AKS if the source freeze cannot be observed, either
queue or a `PROCESSING` row remains, a database/object checksum differs, the
migration gate fails, readiness remains unhealthy, or generated-photo smoke
fails. Keep the source baseline and route unchanged while resolving the issue.

## Limits

This procedure is not a live production migration. The current work has not
performed the source write freeze, a fresh consistent copy, client URL switch,
or source rollback check; A14 remains open until the source path is reachable
and those steps are observed.
