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

helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets --force-update >/dev/null
helm repo add argo https://argoproj.github.io/argo-helm --force-update >/dev/null
helm repo update >/dev/null
"${kubectl_cmd[@]}" create namespace argocd --dry-run=client -o yaml | "${kubectl_cmd[@]}" apply -f - >/dev/null

sealed_chart="$(helm list --namespace kube-system --filter '^sealed-secrets$' \
  --output json "${helm_args[@]}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["chart"] + ":" + rows[0]["status"] if rows else "")')"
if [[ "$sealed_chart" != sealed-secrets-2.20.0:deployed ]]; then
  helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
    --version 2.20.0 --namespace kube-system -f "$project_dir/infra/sealed-secrets/values.yaml" \
    --wait --timeout 5m "${helm_args[@]}" >/dev/null
fi
"${kubectl_cmd[@]}" rollout status deployment/sealed-secrets-controller -n kube-system --timeout=5m >/dev/null
"$script_dir/seal-environment.sh" dev

argocd_chart="$(helm list --namespace argocd --filter '^argocd$' \
  --output json "${helm_args[@]}" | python3 -c 'import json,sys; rows=json.load(sys.stdin); print(rows[0]["chart"] + ":" + rows[0]["status"] if rows else "")')"
if [[ "$argocd_chart" != argo-cd-10.10.3:deployed ]]; then
  helm upgrade --install argocd argo/argo-cd --version 10.10.3 --namespace argocd \
    -f "$project_dir/infra/argocd/values.yaml" -f "$project_dir/infra/argocd/values-dev.yaml" \
    --wait --timeout 10m "${helm_args[@]}" >/dev/null
fi
"${kubectl_cmd[@]}" rollout status deployment/argocd-server -n argocd --timeout=10m >/dev/null
printf '%s\n' 'AKS SealedSecrets and Argo CD are installed; Argo applications remain under explicit bootstrap control.'
