# AKS application access

The album Ingress is handled by one Traefik replica in `ingress-system`. Its web Service is
`ClusterIP`; no application, Grafana, ArgoCD, MinIO console, or S3 write route receives a public IP.
The public AKS API endpoint is a separate management plane and remains restricted to the authorized
workstation `/32`.

Use the dedicated AKS kubeconfig and forward the internal Traefik Service to loopback:

```bash
KUBECONFIG=aks/infra/azure/local/kubeconfig bash aks/scripts/tunnel.sh
```

In a second terminal, send the dev host header:

```bash
curl -H 'Host: album.aks.localhost' http://127.0.0.1:8080/
```

The script only binds `127.0.0.1:8080`; it does not open a listener on the workstation's network
interfaces. Set `KUBE_CONTEXT` only when using another explicitly configured context. If
port-forward runs on an approved VM, an SSH local forward can carry that VM's loopback port to the
workstation. No extra VM, gateway, public ingress IP, or DNS record is created.

The `/originals/` and `/thumbnails/` object route allows GET and HEAD only and preserves the signed
request host, path, and query. MinIO remains an internal Service; its console and PUT/DELETE are not
published. API, ArgoCD, Prometheus, and Grafana administration use their own loopback port-forwards
when those services are installed.
