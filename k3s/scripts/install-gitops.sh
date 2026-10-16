#!/usr/bin/env bash
# Run on dev/prod VM before applying its root Application.
set -euo pipefail
cd "$(dirname "$0")/.."
env_name="${1:-dev}"
case "$env_name" in dev|prod) ;; *) exit 2 ;; esac
helm repo add argo https://argoproj.github.io/argo-helm >/dev/null
helm repo add sealed-secrets https://bitnami.github.io/sealed-secrets >/dev/null
helm repo update >/dev/null
helm upgrade --install sealed-secrets sealed-secrets/sealed-secrets \
  --version 2.20.0 -n kube-system -f infra/sealed-secrets/values.yaml \
  --atomic --wait --timeout 5m >/tmp/kube-study-sealed-secrets-install.log
helm upgrade --install argocd argo/argo-cd --version 10.10.3 \
  -n argocd --create-namespace -f infra/argocd/values.yaml -f "infra/argocd/values-$env_name.yaml" \
  --atomic --wait --timeout 10m >/tmp/kube-study-argocd-install.log
printf '%s\n' 'GitOps controllers installed; credentials remain in cluster Secrets.'
