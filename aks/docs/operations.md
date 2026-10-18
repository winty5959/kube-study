# AKS operations

The learning cluster is `aks-kube-study` in `rg-seonung-aks-test`, under the
`Enterprise부문-아키텍처강화TF` subscription. Use the dedicated `aks-study` kubectl
context. `aks/scripts/aks-power.sh` pins that Azure subscription, resource group, cluster, and
Kubernetes context; it checks that the kubeconfig endpoint matches the selected AKS endpoint.
It does not switch the user's Azure or Kubernetes context.

## Node maintenance

Before draining a node, record the photo row/status and original checksum, all album PDBs, PVC
bindings, PV reclaim policies, and volume topology. Keep two API replicas available so the API PDB
allows one disruption; keep the frontend at two. The command below uses normal eviction and waits
for PDBs. It does not force evictions:

```bash
kubectl --context aks-study drain "$NODE" \
  --ignore-daemonsets --delete-emptydir-data --timeout=10m
```

Verify every StatefulSet is Ready, each Retain PVC is Bound, each disk is attached to the new node,
and the saved original checksum is unchanged. Run the API readiness and public-ingress smoke. Then
uncordon the node, restore the API HPA minimum to one, and restore the `root-dev` and `album-dev`
Argo CD automated sync policies if they were paused for the experiment.

The A11 drain showed that AKS PDBs delay eviction until a replacement is Ready. Azure Disk LRS
volumes briefly reported that they were still attached to the old node; CSI detached and attached
them to the remaining node without a permanent attach failure. See [AKS-NODE](experiments/AKS-NODE.md).

## Stop and start

Stop only after the application has no writes in flight, both Redis job lists are empty, and the
data restore/checksum baseline is recorded. Pause the root and child Argo sync policies. Delete the
dev API HPA temporarily, then scale the API, frontend, and worker deployments to zero. This prevents
the HPA, KEDA, or GitOps from recreating application pods while AKS is stopping. Retain the manifests
in Git; do not delete PVCs or disks.

```bash
bash aks/scripts/aks-power.sh stop
bash aks/scripts/aks-power.sh start
```

The stop helper refuses unless app deployments in each existing namespace are zero, Argo automated
sync is paused, the API HPA is absent, and the expected current context points at this AKS endpoint.
It calls `az aks stop` / `az aks start` for the fixed target, waits for the Azure power and
provisioning states, and on start requires the expected number of Kubernetes nodes to be Ready.
After start, check PVC attachment, database/object readiness, Argo health, metrics, and the restored
photo before restoring GitOps and the HPA. A11 observed a short metrics-server warmup; the HPA and
Argo health recovered after pod metrics became available.

The stop procedure intentionally leaves API, frontend, and worker Deployments at zero and removes
the API HPA. On restart, the HPA will not scale an API whose target replica count is zero. Before
the production manual Sync, restore API replicas to the declared minimum (two in `album-prod`),
wait for the API Pods to be Ready, and confirm the HPA has a valid CPU metric. A manual Sync made
while metrics-server is still warming may stop at Argo's HPA health gate; retry after the HPA
reports `ScalingActive=True`. Keep production automated sync disabled.

Stopping removes AKS node compute charges while it is stopped. Retained disks and other attached
resources may continue to incur charges. Never deallocate the AKS VM scale set directly; do not
delete retained disks as a stop/start shortcut. See [AKS-STOP](experiments/AKS-STOP.md).

## Latest paused state

The release exercise started AKS at 2026-10-18 17:11:29.7528291 UTC; Azure reported start success
at 17:16:30.5467299 UTC. The stop request began at 17:28:35.3096115 UTC, was accepted at
17:28:35.6846421 UTC, and succeeded at 17:30:59.575028 UTC. These are AKS control-plane operation
events, not exact VM billing boundaries. A read-only cluster-state check at 18:19 UTC confirmed
`Stopped` / `Succeeded`. Resource inventory around 18:16 UTC showed the `Standard_D4as_v5` VMSS at
capacity zero with no instances, nine PVC-derived disks `Unattached`, one Standard load balancer,
and one Standard static public IP. The disks mapped to Bound Retain PVs immediately before stop.
No resource was deleted. The partial ActualCost query is pending the 24-hour posting delay; see [cost
reconciliation](cost.md) and [A15 evidence](../../.omo/evidence/aks-implementation/A15-cost-refresh.txt).

Before stopping, both namespaces' app Deployments were zero, API HPAs were absent, dev automated
sync was paused, prod sync remained manual, both Redis queues were empty, no Job was active, dev
retained one intentional `DONE` photo, and prod had zero photo rows. On restart, follow the
verification and restoration sequence above; do not infer that workloads are running while AKS is
stopped. The observed state and disk ownership are recorded in [cleanup inventory](cleanup.md).
