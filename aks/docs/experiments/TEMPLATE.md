# E-XX: AKS experiment title

| Item | Result |
|---|---|
| Run time | YYYY-MM-DD HH:MM KST |
| Environment | `album-dev` or `album-prod` |
| Context | `aks-kube-study` |
| Git revision | |
| Image | tag and observed manifest digest |
| Nodes | node count and relevant placement |
| Result | Pass / Fail / Partial / Not run |

## Purpose and expected behavior

State the Kubernetes behavior being checked and the acceptance criterion from
`.omo/plans/aks-implementation.md`.

## Preconditions

Record relevant Argo CD, workload, HPA/KEDA, PDB, queue, database, and PVC state.
Do not include Secret data, tokens, public IP addresses, kubeconfig content, or
private user data.

## Procedure and observations

Record the actual commands and measured results. Mark any unmeasured time as
approximate. Keep only outputs needed to prove the behavior.

| Time KST | Observation | Evidence |
|---|---|---|
| | | |

## Recovery

Record the Git declaration and runtime state after cleanup. State clearly if
the experiment left an intentional difference.

## Limits

Describe the conditions this result does not cover.
