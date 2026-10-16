#!/usr/bin/env bash
# Build album images on the VM and load them straight into K3S' containerd (M2-M6).
# Run on the VM:  scripts/build-images.sh [TAG] [component...]
#   TAG        image tag, default "dev-<git short sha>" (or "dev-local" outside git)
#   component  api worker frontend minio (default: api worker frontend)
#
# Images keep their GHCR names so manifests do not change when CI starts pushing (M7).
# Pods must use imagePullPolicy IfNotPresent for these locally imported tags.
set -euo pipefail
cd "$(dirname "$0")/.."

REG=ghcr.io/winty5959
TAG="${1:-dev-$(git rev-parse --short HEAD 2>/dev/null || echo local)}"
shift || true
COMPONENTS=("${@:-api worker frontend}")
read -r -a COMPONENTS <<< "${COMPONENTS[*]}"

for c in "${COMPONENTS[@]}"; do
  case "$c" in
    api|worker|frontend) ctx="apps/$c"; image="$REG/album-$c:$TAG" ;;
    minio) ctx="infra/minio"; image="$REG/album-minio:RELEASE.2025-10-15T17-29-55Z" ;;
    *) echo "unknown component: $c" >&2; exit 1 ;;
  esac
  echo "==> $image"
  docker build -q --build-arg APP_VERSION="$TAG" -t "$image" "$ctx" >/dev/null
  docker save "$image" | sudo k3s ctr -n k8s.io images import - >/dev/null
done
echo "imported tag $TAG into k3s"
