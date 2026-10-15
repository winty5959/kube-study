#!/usr/bin/env bash
# Run on the matching VM: scripts/install-monitoring.sh dev|prod
set -euo pipefail
cd "$(dirname "$0")/.."
env_name="${1:?usage: install-monitoring.sh dev|prod}"
case "$env_name" in dev|prod) ;; *) exit 2 ;; esac
kubectl create namespace monitoring --dry-run=client -o yaml | kubectl apply -f - >/dev/null
if ! kubectl -n monitoring get secret grafana-admin >/dev/null 2>&1; then
  umask 077
  task_tmp="$(mktemp -d)"
  trap 'rm -rf "$task_tmp"' EXIT
  printf admin > "$task_tmp/admin-user"
  openssl rand -hex 32 | tr -d '\n' > "$task_tmp/admin-password"
  kubectl -n monitoring create secret generic grafana-admin \
    --from-file=admin-user="$task_tmp/admin-user" \
    --from-file=admin-password="$task_tmp/admin-password" >/dev/null
fi
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null
helm repo update >/dev/null
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 92.7.0 --namespace monitoring \
  -f infra/monitoring/values.yaml -f "infra/monitoring/values-$env_name.yaml" \
  --atomic --wait --timeout 10m > /tmp/kube-study-monitoring-install.log
kubectl apply -k dashboards
kubectl apply -k k8s/monitoring
echo "Monitoring installed; Grafana uses the grafana-admin Secret in monitoring"
