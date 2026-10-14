#!/usr/bin/env bash
# Merge a K3S VM's kubeconfig into the work PC's ~/.kube/config as context "k3s-<env>".
# Usage: scripts/fetch-kubeconfig.sh <dev|prod>
#
# The server address points at the SSH tunnel (scripts/tunnel.sh), not the VM.
# The kubeconfig holds client credentials: it is never written inside the repo or printed.
set -euo pipefail

ENV="${1:?usage: $0 <dev|prod>}"
case "$ENV" in
  dev)  API=16443 ;;
  prod) API=26443 ;;
  *) echo "env must be dev or prod" >&2; exit 1 ;;
esac
NAME="k3s-${ENV}"
KCFG="$HOME/.kube/config"

TMP="$(mktemp)"; trap 'rm -f "$TMP" "$TMP.merged"' EXIT
chmod 600 "$TMP"
ssh "kube-${ENV}" 'cat ~/.kube/config' > "$TMP"

# K3S names cluster, user and context "default"; rename to avoid clashing with other configs
sed -i '' -E \
  -e "s#server: https://127.0.0.1:6443#server: https://127.0.0.1:${API}#" \
  -e "s#^(  *)(name|cluster|user): default\$#\1\2: ${NAME}#" \
  -e "s#^(- *)name: default\$#\1name: ${NAME}#" \
  -e "s#^current-context: default\$#current-context: ${NAME}#" \
  "$TMP"

mkdir -p "$HOME/.kube"
if [ -f "$KCFG" ]; then
  cp "$KCFG" "$KCFG.bak.$(date +%Y%m%d%H%M%S)"
  kubectl config --kubeconfig "$KCFG" delete-context "$NAME" >/dev/null 2>&1 || true
  kubectl config --kubeconfig "$KCFG" delete-cluster "$NAME" >/dev/null 2>&1 || true
  kubectl config --kubeconfig "$KCFG" delete-user    "$NAME" >/dev/null 2>&1 || true
fi
KUBECONFIG="$KCFG:$TMP" kubectl config view --flatten > "$TMP.merged"
install -m 600 "$TMP.merged" "$KCFG"
echo "context ${NAME} registered (server https://127.0.0.1:${API})"
