# AKS experiment results

Each result below was collected in the AKS environment. K3S screenshots and
timestamps are not reused as AKS evidence. See `.omo/plans/aks-implementation.md`
for scenario acceptance criteria and recovery boundaries.

| Experiment | Status | Evidence |
|---|---|---|
| E-01 Pod recovery | Pass | [E-01](E-01.md) |
| E-02 API HPA | Pass | A10 load/HPA evidence: [A10-observability](../../../.omo/evidence/aks-implementation/A10-observability.txt) |
| E-03 KEDA queue scaling | Pass | A10 500-image run: [A10-observability](../../../.omo/evidence/aks-implementation/A10-observability.txt) |
| E-04 rolling update | Pass | [E-04](E-04.md) |
| E-05 failed readiness rollout | Pass | [E-05](E-05.md) |
| E-06 worker OOM retry | Pass | [E-06](E-06.md) |
| E-07 database dependency failure | Pass | [E-07](E-07.md) |
| E-08 persistence after restore | Pass | [AKS-DATA](AKS-DATA.md) |
| E-09 NetworkPolicy | Pass | [E-09](E-09.md) |
| E-10 ConfigMap rollout | Pass | [E-10](E-10.md) |
| E-11 CI-triggered API deployment | Pass; reuses A8 API-only run | [E-11](E-11.md) |
| E-12 self-heal drift | Pass for image drift; annotation drift not detected | [E-12](E-12.md) |
| E-13 release promotion | Pass; owner-merged PR #6, manual prod sync, PostSync smoke, digest comparison, and browser screen check | [E-13](E-13.md) |
| E-14 GitOps rollback | Pass; live Deployment undo showed OutOfSync, manual sync restored the current Git declaration | [E-14](E-14.md) |
| E-15 PreSync deployment gate | Pass; reuses A8 gate run | [E-15](E-15.md) |

Additional AKS operations were separately verified: [data restore](AKS-DATA.md),
[node drain](AKS-NODE.md), and [stop/start](AKS-STOP.md). The cutover rehearsal is
tracked independently in `AKS-CUTOVER.md`.

## Shared recording rules

Use [TEMPLATE.md](TEMPLATE.md). Every run records KST time, context and namespace,
Git SHA, actual image manifest digest, commands, measurements, and recovery state.
Never record Secret values, credentials, kubeconfig content, public IP addresses,
or photo contents. Failures remain failures unless a repeated run satisfies the
acceptance criteria; describe excluded attempts and why they were excluded.
