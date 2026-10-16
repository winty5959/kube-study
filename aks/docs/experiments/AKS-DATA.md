# AKS data restore rehearsal

**Date:** 2026-10-16 KST

**Source:** K3S dev, captured online

**Destination:** AKS dev (`album-dev`)

**Application image:** `sha-b7122b7`

## Source and destination baseline

| Check | K3S dev snapshot | AKS dev before restore |
|---|---:|---:|
| Photo rows | 1 `DONE`, 1,064 bytes | 0 |
| Original objects | 1, 1,064 bytes | 0 |
| Thumbnail objects | 2, 446 bytes total | 0 |
| Main queue | 0 | 0 |
| Processing queues | 0 | 0 |

The K3S dev VM was running during this check and remained running. The snapshot was copied
without stopping K3S writes; it is a dev restore rehearsal, not a final cutover snapshot.
K3S prod remained deallocated. No K3S application data or user traffic was changed.

## Backup and integrity

The source `pg_dump --data-only` and a capsule containing the source row metadata, three object
bodies, content types, sizes, and SHA-256 values were placed in the private AKS MinIO bucket
`migration-backups`, prefix `k3s-dev/2026-10-16/`. The external compressed artifacts were also
copied to the FileVault-protected workstation directory documented in
`aks/docs/data-migration.md`; directory mode is `700`, file mode is `600`.

| Artifact | SHA-256 | Size |
|---|---|---:|
| `database.sql.gz` | `50c601ed5031dadc9989ce7eff6defa98cba9a7b6303e68cc5ae8d3b7c91fbca` | 679 bytes |
| `objects.json.gz` | `93d385d7a0c77e5124f08cad29b17ad0ab4338e0d85f8911ef6c46e997a0cb9b` | 895 bytes |
| `manifest.json` | `e444845ec142973bf8e1d11d09986012739769147ea55e1b3e6efa310244e09b` | 1,111 bytes |

Each source object body was checked against the manifest SHA-256 and byte length. After copying,
each AKS MinIO object was fetched and rechecked against the same values. ETag was not treated as
an MD5 checksum. No backup payload or credential was added to Git.

## Restore and smoke results

- Before restore, Argo automated sync was disabled; the cleanup CronJob was suspended; KEDA was
  paused; worker and API were scaled to zero; and the API HPA was temporarily removed. The
  destination schema and PVCs were retained.
- The first dry-run's verification query used an unqualified table name after the dump set an
  empty `search_path`. PostgreSQL returned `UndefinedTable`; the transaction rolled back. A
  follow-up query confirmed zero destination rows. The dry-run was corrected to use
  `public.photos` and passed: one expected `DONE` row, three object checksums matched, rollback
  verified.
- The validated dump was then applied and committed. The restored row ID, status, filename,
  content type, byte count, and original/small/medium keys matched the source capsule. Final
  target counts were one `DONE` row (1,064 bytes), one original (1,064 bytes), and two
  thumbnails (446 bytes); SHA-256 checks passed. Main and processing queues were empty.
- A restored photo API lookup returned 200 with `DONE`; its original download returned 200 and
  matched the recorded byte count; both thumbnail URLs returned 200 with `image/webp`.
- `aks/scripts/smoke.py` uploaded a generated PNG, observed `DONE`, fetched 200x100 and 800x400
  WebP thumbnails, downloaded the 3,462-byte original, deleted the photo with 204, and confirmed
  the next lookup returned 404.
- HPA metrics briefly reported no sample while the API replica was restarting. Once metrics
  returned, API HPA reported a 4m sample against its 60% CPU request target. The API readiness
  endpoint reported Postgres, Redis, and S3 healthy. Argo was refreshed and returned to Synced/Healthy. The API,
  cleanup, KEDA, and Argo automation were restored; no migration Job or generated smoke photo
  was left behind.

The restored source photo remains in the AKS rehearsal fixture. This run did not freeze source
writes, perform a live traffic switch, or remove the K3S environment.
