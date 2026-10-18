# AKS-STOP: controlled cluster stop and start

## Pre-stop checks

Before stopping AKS, the restored dev photo remained `DONE` at 1,064 bytes with the same original
checksum recorded for AKS-NODE. Redis `thumbnail:jobs` and `thumbnail:processing` both had length
zero. The API, frontend, and worker desired replicas were all zero; the API HPA had been removed
temporarily; and automated sync was paused on `root-dev` and `album-dev`. The data PVCs were Bound.

Ran `bash aks/scripts/aks-power.sh stop` against the fixed Enterprise subscription, resource group,
cluster, and context. Azure Activity Log recorded the stop request Accepted at
2026-10-16T16:27:19Z and Succeeded at 16:29:28Z. The observed final state was
`powerState=Stopped`, `provisioningState=Succeeded`.

## Restart and data validation

Ran `bash aks/scripts/aks-power.sh start`. Azure recorded the start request at 16:30:17Z and
completion at 16:34:42Z. The final state was `powerState=Running`, `provisioningState=Succeeded`,
and the helper observed two Ready nodes on Kubernetes 1.36.4. AKS created new VMSS instances.

All three dev data PVCs remained Bound and attached to the new nodes. PostgreSQL, Redis, and MinIO
returned Ready with their existing data. The API HPA was recreated with minReplicas 1; after its
initial metrics-server warmup, CPU metrics were available again and the API HPA reported 3% of its
60% target. Argo root-dev and album-dev returned to Synced/Healthy with automated sync enabled.

Post-start readiness returned Postgres, Redis, and S3 `ok`. A generated image reached DONE; both
thumbnails, original download, and DELETE passed. The original API row remained the only row and
its 1,064-byte original SHA-256 matched the pre-stop checksum. The generated smoke fixture was
deleted. AKS remains Running for A12 onward; K3S was not modified.

## Temporary cost pause while PR #5 awaits review

Before 2026-10-18 13:11:54 UTC, confirmed there were no active workload jobs and both
Redis queues were empty. `album-dev` contained the intentional migrated photo as its only row;
`album-prod` contained zero photo rows. The prod smoke failure remained historical and its fixture
had already been deleted. Before stopping, API, frontend, and worker replicas were set to zero in
both namespaces, the API HPAs were removed, and automated sync was paused on `root-dev` and
`album-dev`. Prod remains manual. No PVC or Azure resource was deleted.

The power helper initially refused to run because its pinned Kubernetes context was incorrectly
set to `aks-kube-study`; the actual context is `aks-study`. The helper and operations example were
corrected, and shell syntax/lint checks passed. The corrected `bash aks/scripts/aks-power.sh stop`
then completed successfully. Azure Activity Log recorded Stop Managed Cluster as Started at
13:11:54.738Z, Accepted at 13:11:55.144Z, and Succeeded at 13:15:26.061Z. At 13:22 UTC, Azure
reported `powerState=Stopped`, `provisioningState=Succeeded`, and configured node count two. All nine
`StandardSSD_LRS` disks (33 GiB total) reported `Unattached`; immediately before the stop they
mapped to nine Bound `Retain` PVCs. This records the current temporary pause, not a new full A11
stop/start experiment. K3S was not modified.

After PR #5 review and merge, start AKS with the helper and verify two Ready nodes, nine Bound
PVCs, and application data/readiness. Restore `root-dev` and `album-dev` automated sync with
`prune: true` and `selfHeal: true`, then verify dev desired workloads recover. Keep prod manual
until the new immutable release digest is explicitly synced and A12 smoke passes. Resume E-13/E-14
only after that release gate. A post-stop ActualCost query has not yet been recorded.
