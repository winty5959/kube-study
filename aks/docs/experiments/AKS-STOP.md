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
