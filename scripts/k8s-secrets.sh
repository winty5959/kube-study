#!/usr/bin/env bash
# Create k8s/overlays/<env>/secrets.env with random credentials for kustomize's secretGenerator.
# Run on the VM. The file is gitignored and never printed; it is replaced by SealedSecrets in M8.
# Usage: scripts/k8s-secrets.sh <dev|prod>
set -euo pipefail
cd "$(dirname "$0")/.."

ENV="${1:?usage: $0 <dev|prod>}"
FILE="k8s/overlays/${ENV}/secrets.env"
[ -d "$(dirname "$FILE")" ] || { echo "no overlay for $ENV" >&2; exit 1; }
if [ -f "$FILE" ]; then
  echo "$FILE already exists; leaving it untouched"
  exit 0
fi
umask 077
cat > "$FILE" <<EOF
POSTGRES_PASSWORD=$(openssl rand -hex 16)
S3_ACCESS_KEY=album-$(openssl rand -hex 4)
S3_SECRET_KEY=$(openssl rand -hex 16)
EOF
echo "$FILE created (mode 600)"
