# AKS decisions and preflight

Last checked: 2026-10-16 KST. Azure subscription context: `AX사업부문-인프라아키텍처팀` (Enabled). The selected subscription is registered to a tenant different from the previously planned `ktopen.onmicrosoft.com`; the user's latest instruction selects the AX subscription.

Detailed command results: [A0 preflight evidence](../../.omo/evidence/aks-implementation/A0-preflight.txt).

## A0 observations

| Check | Result | Decision/status |
|---|---|---|
| Existing K3S resource group | `rg-seonung-kube-study`, `koreacentral` | Keep for K3S; do not reuse for AKS. |
| AKS resource group candidate | `rg-seonung-kube-study-aks` | Not present in the selected subscription. No AKS resource has been created. |
| Region | `koreacentral` | Retained as the plan candidate. |
| Kubernetes versions | 1.36 is default; 1.37 is listed as available | Prefer the current default after confirming API and addon compatibility during A3. |
| Planned `Standard_F4s_v2` | 4 vCPU / 8 GiB, but Azure reports `NotAvailableForSubscription` in `koreacentral` | A0 cannot approve this SKU. No alternate SKU or region was selected. |
| Documented alternative `Standard_D4as_v5` | 4 vCPU / 16 GiB, no SKU restriction returned | Candidate only; requires an explicit plan decision because it changes the planned SKU and cost. |
| Quota | 30/354 regional vCPU; FSv2 0/350; DAsv5 14/350 | The currently reported family and regional limits have headroom; this does not override SKU availability. |
| Azure providers | ContainerService, Compute, Network, ManagedIdentity, Storage are Registered | No provider registration is required at this point. |
| Existing subscription VNets and connections | 5 VNets / 11 address ranges across 6 resource groups; no overlap with the proposed VNet, node, pod, or service ranges. No VNet peering, VPN connection, local gateway, or VNet gateway found. | Subscription-level check only; organization/VPN routes outside this subscription still need confirmation. |
| Current user's roles | Contributor found for the user and security-group assignments | No role-assignment administrator role was found. Confirm who can grant the needed AKS Azure RBAC access before relying on Entra/Azure RBAC administration. |

## Pending before A3

- Select an available node SKU or make the planned SKU available in this subscription.
- Confirm an authorized identity/group can administer AKS Azure RBAC without enabling local admin credentials.
- Confirm the proposed CIDRs do not overlap organization or VPN routes outside the inspected subscription.
- Recalculate the cost baseline for the selected SKU and retrieve the current management source CIDR for a restricted public API endpoint, if that endpoint remains the approved design.

No AKS deployment, role assignment, provider registration, or network change has been made.
