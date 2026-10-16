#!/usr/bin/env bash
# Run on the matching VM before applying the album overlay.
set -euo pipefail
cd "$(dirname "$0")/.."
helm repo add kedacore https://kedacore.github.io/charts >/dev/null
helm repo update >/dev/null
helm upgrade --install keda kedacore/keda --version 2.21.0 \
  --namespace keda --create-namespace -f infra/keda/values.yaml \
  --atomic --wait --timeout 5m > /tmp/kube-study-keda-install.log
echo 'KEDA installed'
