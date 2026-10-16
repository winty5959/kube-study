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

helm repo add kedacore https://kedacore.github.io/charts --force-update >/dev/null
helm repo update >/dev/null
"${kubectl_cmd[@]}" create namespace keda --dry-run=client -o yaml | "${kubectl_cmd[@]}" apply -f - >/dev/null
keda_chart="$(helm list --namespace keda --filter '^keda$' \
  --output json "${helm_args[@]}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["chart"] + ":" + rows[0]["status"] if rows else "")')"
if [[ "$keda_chart" != keda-2.21.0:deployed ]]; then
  helm upgrade --install keda kedacore/keda --version 2.21.0 --namespace keda \
    -f "$project_dir/infra/keda/values.yaml" --server-side=false \
    --wait --timeout 10m "${helm_args[@]}" >/dev/null
fi
"${kubectl_cmd[@]}" rollout status deployment/keda-operator -n keda --timeout=5m >/dev/null
"${kubectl_cmd[@]}" rollout status deployment/keda-operator-metrics-apiserver -n keda --timeout=5m >/dev/null
"${kubectl_cmd[@]}" rollout status deployment/keda-admission-webhooks -n keda --timeout=5m >/dev/null
printf '%s\n' 'KEDA operator, metrics API, and admission webhooks are ready.'
