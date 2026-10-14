#!/usr/bin/env bash
# Mirror the working tree from the work PC to the VM for fast edit-run loops
# (no commit needed). Git remains the source of truth.
# Usage: scripts/sync.sh [dev|prod]   -> ~/kube-study on the VM
set -euo pipefail

ENV="${1:-dev}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

rsync -az --delete \
  --exclude .git/ --exclude .venv/ --exclude __pycache__/ \
  --exclude .pytest_cache/ --exclude .ruff_cache/ \
  --exclude graphify-out/ --exclude .codegraph/ --exclude .DS_Store \
  --filter=':- .gitignore' \
  "$ROOT/" "kube-${ENV}:kube-study/"
echo "synced to kube-${ENV}:~/kube-study"
