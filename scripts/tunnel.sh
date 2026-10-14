#!/usr/bin/env bash
# Forward cluster ports from a K3S VM to the work PC over SSH.
# Usage: scripts/tunnel.sh <dev|prod> [start|stop|status]
#
#   Ingress (Traefik :80) -> localhost:8080 (dev) / 8090 (prod)
#   K8s API (:6443)       -> localhost:16443 (dev) / 26443 (prod)
#
# Requires an ~/.ssh/config host alias "kube-<env>" (see docs/azure-vm.md).
# ArgoCD / Grafana UIs are exposed later through Ingress hostnames on the same port.
set -euo pipefail

ENV="${1:?usage: $0 <dev|prod> [start|stop|status]}"
CMD="${2:-start}"
case "$ENV" in
  dev)  HTTP=8080; API=16443 ;;
  prod) HTTP=8090; API=26443 ;;
  *) echo "env must be dev or prod" >&2; exit 1 ;;
esac
HOST="kube-${ENV}"
SOCK="${TMPDIR:-/tmp}/kube-tunnel-${ENV}.sock"

case "$CMD" in
  start)
    if ssh -S "$SOCK" -O check "$HOST" 2>/dev/null; then echo "already running"; exit 0; fi
    ssh -f -N -M -S "$SOCK" \
      -o ExitOnForwardFailure=yes -o ServerAliveInterval=30 \
      -L "${HTTP}:127.0.0.1:80" -L "${API}:127.0.0.1:6443" "$HOST"
    echo "tunnel ${ENV} up: http://localhost:${HTTP}  api https://127.0.0.1:${API}"
    ;;
  stop)   ssh -S "$SOCK" -O exit "$HOST" 2>/dev/null || echo "not running" ;;
  status) ssh -S "$SOCK" -O check "$HOST" ;;
  *) echo "unknown command: $CMD" >&2; exit 1 ;;
esac
