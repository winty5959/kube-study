# AKS observability

The AKS cluster runs one kube-prometheus-stack installation in `monitoring`. The values keep
the etcd, kube-controller-manager, kube-scheduler, and kube-proxy scrapes disabled because this
managed control plane does not expose those targets. Metrics Server is enabled for HPA and is
independent from Prometheus. Azure managed Prometheus and Container Insights are not enabled.

Prometheus accepts the `monitoring` release label for ServiceMonitors and PrometheusRules. The
album API and worker ServiceMonitors select only `album-dev` and `album-prod`; this keeps metrics
collection scoped to the two application environments. `AlbumQueueBacklog`, `AlbumAPIErrorRate`,
and `AlbumCrashLoop` are provisioned by the album PrometheusRule.

Five Grafana dashboards provision from `aks/dashboards/`. The checker retrieves each provisioned
dashboard from Grafana, runs every panel expression against Prometheus for the selected namespace,
and requires a finite sample. It also checks all three expected alert names. Run it from a machine
with the intended AKS kubectl context and `kubectl` available on `PATH`:

```sh
python3 aks/scripts/check-observability.py dev
python3 aks/scripts/check-observability.py prod
```

`aks/scripts/check-observability.py` uses only the Python standard library. It starts local
port-forwards for the Grafana and Prometheus services, reads the Grafana credential Secret in
memory, and stops both port-forwards on exit. It never prints the credential or response body.

The A10 acceptance run found all 20 dev dashboard panels returning finite live samples and all
three alerts loaded. The API HPA reached its three-replica maximum during the 200-VU run. The
500-image exercise populated worker metrics and the KEDA worker deployment reached two replicas.
See [A10 evidence](../../.omo/evidence/aks-implementation/A10-observability.txt) for measured
requests, load results, recovery state, and the failed first load-harness attempt.

The 200-VU run briefly drove one node to 85% observed CPU while the other was at 23%. The API
remained healthy and the node requests remained below the 80% acceptance limit. This is a useful
capacity boundary for the two-node D4as_v5 learning cluster, not a production traffic guarantee.
