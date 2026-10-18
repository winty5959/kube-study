# AKS decisions and preflight

Last checked: 2026-10-18 14:40 UTC. The user first selected `AX사업부문-인프라아키텍처팀`, then explicitly replaced that target with the `Enterprise부문-아키텍처강화TF` subscription and authorized using its Owner access to grant the required AKS roles. The cluster is deployed in `rg-seonung-aks-test`, `koreacentral`.

Detailed results: [Enterprise A0 recheck](../../.omo/evidence/aks-implementation/A0-preflight-enterprise.txt) and [A3 deployment evidence](../../.omo/evidence/aks-implementation/A3-provision.txt). The earlier [AX preflight](../../.omo/evidence/aks-implementation/A0-preflight.txt) is retained as historical evidence for the superseded target.

## Current decisions

| Check | Result | Decision/status |
|---|---|---|
| Existing K3S resource group | `rg-seonung-kube-study`, `koreacentral` | Keep K3S resources and data isolated. |
| AKS resource group | `rg-seonung-aks-test` | Created in the user-selected Enterprise subscription. |
| Cluster | `aks-kube-study`, `koreacentral`, Kubernetes 1.36 | Provisioning succeeded; power state Stopped as of 14:40 UTC; AKS Base / Free management tier. |
| Node SKU | Two configured `Standard_D4as_v5`, each 4 vCPU / 16 GiB | Selected after `Standard_F4s_v2` returned `NotAvailableForSubscription`; both nodes were Ready before the stop. |
| Network | Azure CNI Overlay, Cilium, isolated VNet; three workstation IPv4 `/32` ranges on the public API endpoint | Previous management egress addresses remain authorized; the current address was added after the workstation location changed. Proposed CIDRs do not overlap inspected VNets/subnets in the selected subscription. Organization routes outside it are not checked. |
| Identity | Entra managed identity, Azure RBAC, local accounts disabled | Signed-in user has Cluster User and cluster-scope RBAC Cluster Admin roles on this test cluster. |
| Cost | Public retail baseline about `$354.83/month` | Estimate includes two D4as_v5 nodes and current fixed items; enterprise discounts, tax, I/O, traffic, backups, and actual billing remain excluded. |
| Azure providers | ContainerService, Compute, Network, ManagedIdentity, Storage are Registered | No provider registration was needed. |

The workstation's literal authorized IPs are intentionally omitted. If its egress address changes, refresh the authorized ranges before using the public API endpoint. The subscription-level network scan does not establish that external corporate or VPN routes cannot overlap.

## Next infrastructure work

A0-A11 and A14 are complete with recorded evidence. The dev Album UI was rechecked after resuming AKS; its existing card, thumbnail, and detail image loaded successfully. A12 is at PR #6 (`aks-v1.0.1`): the four release aliases match current dev digests, but human review/merge and the manual prod Sync/smoke remain pending. A13 E-13/E-14 depend on A12. A15 has only partial ActualCost dates and needs a later posting query. AKS was stopped at 14:38 UTC while awaiting review; Azure reported `powerState=Stopped` and `provisioningState=Succeeded` at 14:40 UTC. Dev had been available and prod app replicas were zero before the stop. K3S traffic and data cutover remain out of scope.
