# AKS decisions and preflight

Last checked: 2026-10-16 KST. The user first selected `AX사업부문-인프라아키텍처팀`, then explicitly replaced that target with the `Enterprise부문-아키텍처강화TF` subscription and authorized using its Owner access to grant the required AKS roles. The cluster is deployed in `rg-seonung-aks-test`, `koreacentral`.

Detailed results: [Enterprise A0 recheck](../../.omo/evidence/aks-implementation/A0-preflight-enterprise.txt) and [A3 deployment evidence](../../.omo/evidence/aks-implementation/A3-provision.txt). The earlier [AX preflight](../../.omo/evidence/aks-implementation/A0-preflight.txt) is retained as historical evidence for the superseded target.

## Current decisions

| Check | Result | Decision/status |
|---|---|---|
| Existing K3S resource group | `rg-seonung-kube-study`, `koreacentral` | Keep K3S resources and data isolated. |
| AKS resource group | `rg-seonung-aks-test` | Created in the user-selected Enterprise subscription. |
| Cluster | `aks-kube-study`, `koreacentral`, Kubernetes 1.36 | Provisioning succeeded; AKS Base / Free management tier. |
| Node SKU | Two `Standard_D4as_v5`, each 4 vCPU / 16 GiB | Selected after `Standard_F4s_v2` returned `NotAvailableForSubscription`; both nodes are Ready. |
| Network | Azure CNI Overlay, Cilium, isolated VNet; one current management `/32` on the public API endpoint | Proposed CIDRs do not overlap inspected VNets/subnets in the selected subscription. Organization routes outside it are not checked. |
| Identity | Entra managed identity, Azure RBAC, local accounts disabled | Signed-in user has Cluster User and cluster-scope RBAC Cluster Admin roles on this test cluster. |
| Cost | Public retail baseline about `$354.83/month` | Estimate includes two D4as_v5 nodes and current fixed items; enterprise discounts, tax, I/O, traffic, backups, and actual billing remain excluded. |
| Azure providers | ContainerService, Compute, Network, ManagedIdentity, Storage are Registered | No provider registration was needed. |

The workstation's literal authorized IP is intentionally omitted. If its egress address changes, refresh the single authorized range before using the public API endpoint. The subscription-level network scan does not establish that external corporate or VPN routes cannot overlap.

## Next infrastructure work

A3 is complete. A4 verifies a dedicated Azure Disk StorageClass and claim behavior; A5 configures internal-only Traefik and network policy; A6 bootstraps independent secrets and data services. No K3S traffic cutover is part of these steps.
