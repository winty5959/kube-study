#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
kubeconfig="${KUBECONFIG:-$project_dir/infra/azure/local/kubeconfig}"
kube_context="${KUBE_CONTEXT:-aks-study}"
kubectl_cmd=(kubectl --kubeconfig "$kubeconfig" --context "$kube_context")
helm_args=(--kubeconfig "$kubeconfig" --kube-context "$kube_context")
export HELM_CONFIG_HOME="${HELM_CONFIG_HOME:-/tmp/aks-helm-config}"
export HELM_CACHE_HOME="${HELM_CACHE_HOME:-/tmp/aks-helm-cache}"
export HELM_DATA_HOME="${HELM_DATA_HOME:-/tmp/aks-helm-data}"

environment="${1:?usage: install-monitoring.sh dev}"
[[ "$environment" == dev ]] || { echo 'AKS currently supports dev monitoring only' >&2; exit 2; }
for statefulset in postgres redis minio; do
  "${kubectl_cmd[@]}" rollout status "statefulset/$statefulset" -n album-dev --timeout=5m >/dev/null
done
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts --force-update >/dev/null
helm repo update >/dev/null
"$script_dir/seal-environment.sh" dev
monitoring_chart="$(helm list --namespace monitoring --filter '^monitoring$' \
  --output json "${helm_args[@]}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["chart"] + ":" + rows[0]["status"] if rows else "")')"
if [[ "$monitoring_chart" != kube-prometheus-stack-92.7.0:deployed ]]; then
  helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
    --version 92.7.0 --namespace monitoring \
    -f "$project_dir/infra/monitoring/values.yaml" \
    -f "$project_dir/infra/monitoring/values-dev.yaml" \
    --wait --timeout 20m "${helm_args[@]}" >/dev/null
fi
"${kubectl_cmd[@]}" apply -k "$project_dir/dashboards" >/dev/null
"${kubectl_cmd[@]}" apply -k "$project_dir/k8s/monitoring" >/dev/null
"${kubectl_cmd[@]}" rollout status deployment/monitoring-grafana -n monitoring --timeout=10m >/dev/null
"${kubectl_cmd[@]}" rollout status deployment/monitoring-kube-prometheus-operator -n monitoring --timeout=10m >/dev/null
"${kubectl_cmd[@]}" rollout status statefulset/prometheus-monitoring-kube-prometheus-prometheus -n monitoring --timeout=10m >/dev/null
"${kubectl_cmd[@]}" rollout status statefulset/alertmanager-monitoring-kube-prometheus-alertmanager -n monitoring --timeout=10m >/dev/null
for claim in data-postgres-0 data-redis-0 data-minio-0; do
  phase="$("${kubectl_cmd[@]}" get pvc "$claim" -n album-dev -o jsonpath='{.status.phase}')"
  [[ "$phase" == Bound ]] || { echo "Data claim is not Bound: $claim" >&2; exit 1; }
done
for claim in monitoring-grafana prometheus-monitoring-kube-prometheus-prometheus-db-prometheus-monitoring-kube-prometheus-prometheus-0 alertmanager-monitoring-kube-prometheus-alertmanager-db-alertmanager-monitoring-kube-prometheus-alertmanager-0; do
  phase="$("${kubectl_cmd[@]}" get pvc "$claim" -n monitoring -o jsonpath='{.status.phase}')"
  [[ "$phase" == Bound ]] || { echo "Monitoring claim is not Bound: $claim" >&2; exit 1; }
done
printf '%s\n' 'Prometheus stack and AKS monitoring resources are ready.'
