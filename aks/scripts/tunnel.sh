#!/usr/bin/env bash
set -euo pipefail

context="${KUBE_CONTEXT:-aks-study}"
kubectl --context "$context" get namespace ingress-system >/dev/null
exec kubectl --context "$context" -n ingress-system port-forward \
  service/traefik 8080:80 --address 127.0.0.1
