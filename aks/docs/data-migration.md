# K3S to AKS data rehearsal

This runbook covers a **development restore rehearsal** for the album service. It does not
authorize or prove a live traffic cutover. The rehearsal snapshot was captured while K3S dev
remained online, so it is not a point-in-time-consistent final migration snapshot. For a real
cutover, schedule a separate write freeze, drain and inspect both Redis queues and all
`PROCESSING` rows, capture a fresh database dump and object set, then verify the destination
before changing client traffic.

## Current rehearsal snapshot

The 2026-10-16 KST K3S dev inspection found one `DONE` photo row (1,064 bytes), one original
object (1,064 bytes), two thumbnail objects (446 bytes total), and empty main and processing
queues. The source was not paused and was not modified. AKS dev had no photo rows or app-bucket
objects before restore. The source and target facts, dump hashes, and execution results are in
`.omo/evidence/aks-implementation/A9-data-restore.txt`.

The private AKS `migration-backups` bucket holds the transfer copy at
`k3s-dev/2026-10-16/`. A second copy of `database.sql.gz`, `objects.json.gz`, and `manifest.json`
is stored outside the repository at:

```text
~/.local/share/kube-study/aks-backups/k3s-dev/2026-10-16/
```

The host reported FileVault enabled. The backup directory is mode `700` and the three files are
mode `600`. Their contents include photo data and database metadata; keep them private and out
of Git, logs, and Graphify input. The external compressed dump and object capsule SHA-256 values
must match the evidence record before use.

## Restore procedure

1. Confirm the source row, bucket object counts and bytes, object SHA-256 values, and both Redis
   queues. Do not infer an empty source from VM or PVC recovery evidence. If this is a final
   migration, stop writes under a separately scheduled window before taking the snapshot.
2. Save and inspect the target fixture. Confirm the schema migration version and image digest.
   Do not reset or replace destination PVCs.
3. Before restoring, disable the target Argo automated sync, suspend cleanup, pause KEDA, stop
   the worker, remove the API HPA temporarily, and scale the API to zero. Verify no cleanup job
   is active. Do not flush Redis or treat a missing queue entry as proof that a `PROCESSING` row
   can be discarded.
4. Keep the source database dump and object manifest together. Copy originals and thumbnails
   while checking each key, byte length, and SHA-256. ETag is not assumed to be MD5.
5. Run a transactional dry-run against the intended destination schema, compare the row ID,
   status, object keys, content type, and size with the capsule, then roll it back and verify
   the destination row count is still zero. The dump changes `search_path`; verification queries
   must qualify `public.photos`.
6. Apply the same validated SQL in a transaction and commit only after row and object checks
   pass. This rehearsal used the same API image and schema as the deployed dev application.
7. Re-enable the API HPA, API deployment, KEDA, cleanup, and Argo automated sync. Confirm
   Argo is Synced/Healthy, readiness checks pass, queues are empty, and the worker returns to
   zero replicas after processing.
8. Read and download a restored photo through the application. Then run
   `SMOKE_HOST=album.aks.localhost python3 aks/scripts/smoke.py http://127.0.0.1:8080` through
   the loopback Traefik tunnel. The smoke must upload, reach `DONE`, read both thumbnails and
   the original, delete the fixture, and confirm the deleted row returns 404.

If a dry-run, checksum, row, or object check fails, roll back the target transaction, keep the
source untouched, and leave target writes and cleanup paused while investigating. Restore only
the identified rehearsal fixture from a validated snapshot. Never delete data on the source to
make a target check pass.

## Result and boundary

The rehearsal restored the one existing photo and all three objects into AKS dev. The original
row and each object matched the source capsule; API reads and downloads succeeded. A generated
photo also completed upload, thumbnail, original-download, and deletion checks. The restored
photo and its objects remain in AKS dev as the preserved fixture. The separate local backup and
the private AKS backup prefix remain available for further rehearsals.

K3S dev remained online and its data was preserved. No source traffic was redirected. Because
the snapshot was taken without a write freeze, do not use it as proof of final cutover
consistency.
