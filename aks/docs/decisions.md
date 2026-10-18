# AKS decisions and preflight

Last checked: 2026-10-18 17:31 UTC. The user first selected `AX사업부문-인프라아키텍처팀`, then explicitly replaced that target with the `Enterprise부문-아키텍처강화TF` subscription and authorized using its Owner access to grant the required AKS roles. The cluster is deployed in `rg-seonung-aks-test`, `koreacentral`.

Detailed results: [Enterprise A0 recheck](../../.omo/evidence/aks-implementation/A0-preflight-enterprise.txt) and [A3 deployment evidence](../../.omo/evidence/aks-implementation/A3-provision.txt). The earlier [AX preflight](../../.omo/evidence/aks-implementation/A0-preflight.txt) is retained as historical evidence for the superseded target.

## Current decisions

| Check | Result | Decision/status |
|---|---|---|
| Existing K3S resource group | `rg-seonung-kube-study`, `koreacentral` | Keep K3S resources and data isolated. |
| AKS resource group | `rg-seonung-aks-test` | Created in the user-selected Enterprise subscription. |
| Cluster | `aks-kube-study`, `koreacentral`, Kubernetes 1.36 | Provisioning succeeded; power state Stopped at 17:30:59 UTC after A12/A13 acceptance; AKS Base / Free management tier. |
| Node SKU | Two configured `Standard_D4as_v5`, each 4 vCPU / 16 GiB | Selected after `Standard_F4s_v2` returned `NotAvailableForSubscription`; both nodes were Ready before the stop. |
| Network | Azure CNI Overlay, Cilium, isolated VNet; three workstation IPv4 `/32` ranges on the public API endpoint | Previous management egress addresses remain authorized; the current address was added after the workstation location changed. Proposed CIDRs do not overlap inspected VNets/subnets in the selected subscription. Organization routes outside it are not checked. |
| Identity | Entra managed identity, Azure RBAC, local accounts disabled | Signed-in user has Cluster User and cluster-scope RBAC Cluster Admin roles on this test cluster. |
| Cost | Public retail baseline about `$354.83/month` | Estimate includes two D4as_v5 nodes and current fixed items; enterprise discounts, tax, I/O, traffic, backups, and actual billing remain excluded. |
| Azure providers | ContainerService, Compute, Network, ManagedIdentity, Storage are Registered | No provider registration was needed. |

The workstation's literal authorized IPs are intentionally omitted. If its egress address changes, refresh the authorized ranges before using the public API endpoint. The subscription-level network scan does not establish that external corporate or VPN routes cannot overlap.

## Next infrastructure work

A0-A14 are complete with recorded evidence. The dev Album UI and the prod empty gallery were both checked in a browser. Owner-merged PR #6 was manually deployed to prod; its smoke and four runtime digest checks passed. GitHub reported no separate review or PR checks. E-13 and E-14 passed with prod automated sync disabled. AKS was safely stopped at 17:30:59 UTC; its D4as_v5 node pool is configured for two but the VMSS capacity is zero, and all nine managed disks are Unattached after mapping to Bound Retain PVCs before stop. A15 has partial KRW ActualCost through Oct 18, and the short Oct 18 restart/release/stop period has not posted. Re-query after 24–48 hours before claiming a final actual-versus-estimate comparison. K3S traffic and data cutover remain out of scope.
