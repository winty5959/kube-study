# AKS operations

The learning cluster is `aks-kube-study` in `rg-seonung-aks-test`, under the
`Enterprise부문-아키텍처강화TF` subscription. Use the dedicated `aks-kube-study` kubectl
context. `aks/scripts/aks-power.sh` pins that Azure subscription, resource group, cluster, and
Kubernetes context; it checks that the kubeconfig endpoint matches the selected AKS endpoint.
It does not switch the user's Azure or Kubernetes context.

## Node maintenance

Before draining a node, record the photo row/status and original checksum, all album PDBs, PVC
bindings, PV reclaim policies, and volume topology. Keep two API replicas available so the API PDB
allows one disruption; keep the frontend at two. The command below uses normal eviction and waits
for PDBs. It does not force evictions:

```bash
kubectl --context aks-kube-study drain "$NODE" \
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

Stopping removes AKS node compute charges while it is stopped. Retained disks and other attached
resources may continue to incur charges. Never deallocate the AKS VM scale set directly; do not
delete retained disks as a stop/start shortcut. See [AKS-STOP](experiments/AKS-STOP.md).
