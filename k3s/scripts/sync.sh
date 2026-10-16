#!/usr/bin/env bash
# Mirror the working tree from the work PC to the VM for fast edit-run loops
# (no commit needed). Git remains the source of truth.
set -euo pipefail

ENV="${1:-}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

case "$ENV" in
  dev|prod) ;;
  *) echo "usage: $0 <dev|prod>" >&2; exit 2 ;;
esac

# protect: --delete must never remove VM-only files such as the compose .env (credentials)
rsync -az --delete \
  --filter='protect .env' --filter='protect .env.*' --filter='protect secrets.env' \
  --filter='protect *.pem' --filter='protect *.key' --filter='protect sealed-secrets-key*' \
  --filter='protect .venv/' \
  --exclude .git/ --exclude .venv/ --exclude __pycache__/ \
  --exclude .pytest_cache/ --exclude .ruff_cache/ \
  --exclude graphify-out/ --exclude .codegraph/ --exclude .DS_Store \
  --filter=':- .gitignore' \
  "$ROOT/" "kube-${ENV}:kube-study/k3s/"
echo "synced to kube-${ENV}:~/kube-study/k3s"
