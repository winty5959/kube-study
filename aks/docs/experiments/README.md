# AKS experiment results

Each result below was collected in the AKS environment. K3S screenshots and
timestamps are not reused as AKS evidence. See `.omo/plans/aks-implementation.md`
for scenario acceptance criteria and recovery boundaries.

| Experiment | Status | Evidence |
|---|---|---|
| E-01 Pod recovery | Pass | [E-01](E-01.md) |
| E-02 API HPA | Pass | A10 load/HPA evidence: [A10-observability](../../../.omo/evidence/aks-implementation/A10-observability.txt) |
| E-03 KEDA queue scaling | Pass | A10 500-image run: [A10-observability](../../../.omo/evidence/aks-implementation/A10-observability.txt) |
| E-04 rolling update | Not run | |
| E-05 failed readiness rollout | Not run | |
| E-06 worker OOM retry | Not run | |
| E-07 database dependency failure | Not run | |
| E-08 persistence after restore | Pass | [AKS-DATA](AKS-DATA.md) |
| E-09 NetworkPolicy | Not run | |
| E-10 ConfigMap rollout | Not run | |
| E-11 CI-triggered API deployment | Not run | |
| E-12 self-heal drift | Not run | |
| E-13 release promotion | Pending release PR review, merge, and manual sync | [release workflow](../release.md) |
| E-14 GitOps rollback | Not run; requires E-13 | |
| E-15 PreSync deployment gate | Not run | |

Additional AKS operations were separately verified: [data restore](AKS-DATA.md),
[node drain](AKS-NODE.md), and [stop/start](AKS-STOP.md). The cutover rehearsal is
tracked independently in `AKS-CUTOVER.md`.

## Shared recording rules

Use [TEMPLATE.md](TEMPLATE.md). Every run records KST time, context and namespace,
Git SHA, actual image manifest digest, commands, measurements, and recovery state.
Never record Secret values, credentials, kubeconfig content, public IP addresses,
or photo contents. Failures remain failures unless a repeated run satisfies the
acceptance criteria; describe excluded attempts and why they were excluded.
