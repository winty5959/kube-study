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

**The dev-only source snapshot, target comparison, AKS test-client selection,
generated-photo smoke, and K3S recovery passed on 2026-10-17 KST.** The K3S
write path was frozen by pausing `root-dev` and `album-dev` auto-sync, suspending
`album-cleanup`, pausing the worker ScaledObject, deleting the API and worker
HPAs, and scaling the API and worker to zero. With no active jobs, no
`PROCESSING` rows, and both Redis queues empty, a fresh data-only PostgreSQL
dump and object manifest were captured. The AKS dev row and all three object
bodies already matched that frozen source by key, size, and SHA-256, so no
database or object restore was reapplied. See [A14 evidence](../../../.omo/evidence/aks-implementation/A14-cutover-rehearsal.txt).

The generated-photo smoke used only the AKS loopback Traefik route
`http://127.0.0.1:18080` with `Host: album.aks.localhost`; it reached `DONE`,
read the original and both thumbnails, and deleted the fixture. K3S dev then
recovered to Synced/Healthy with its original row and object checksums intact.
Public DNS, K3S prod, and real user traffic were not changed.

## Rehearsal procedure

1. Open the documented K3S dev SSH tunnel and verify `k3s-dev`, the album app,
   the source PostgreSQL, object store, and both Redis queues. If the source
   cannot be reached, stop here; do not infer it is empty or stopped.
2. Record source row/status/byte counts, object keys/sizes/SHA-256 values, both
   queues, image/schema version, and a verified restore baseline. Record the
   short write-freeze window before pausing the dev API, worker,
   cleanup, HPA/KEDA, and GitOps paths that can create or process writes.
3. Confirm no request or job can write, both queues are empty, and there are no
   `PROCESSING` rows. Capture a new database dump and object manifest, then
   verify each target body by size and SHA-256. Keep all payloads outside Git.
4. Pause AKS dev writes and cleanup. Compare row state, object keys, bytes,
   checksums, schema version, and queues with the frozen source. If they already
   match, record that no restore is required. If they differ, validate and
   apply only the required snapshot data without replacing PVCs, then compare
   again before resuming the AKS API and worker.
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

This procedure is not a live production migration. A14 selected the AKS route
only for a loopback test client; it did not change DNS, route real users, modify
K3S prod, or delete the K3S source. A final production migration still needs a
separately approved traffic plan and source-retirement decision.
