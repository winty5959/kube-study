#!/usr/bin/env bash
# Run on the environment VM after installing the controller. Never print plaintext.
set -euo pipefail
cd "$(dirname "$0")/.."
env_name="${1:?usage: seal-environment.sh dev|prod}"
case "$env_name" in dev|prod) ;; *) exit 2 ;; esac
umask 077
mkdir -p "k8s/secrets/$env_name/album" "k8s/secrets/$env_name/monitoring" "$HOME/.local/share/kube-study"
kubectl -n "album-$env_name" create secret generic album-secrets \
  --from-env-file="k8s/overlays/$env_name/secrets.env" --dry-run=client -o json \
  | kubeseal --controller-name sealed-secrets-controller --controller-namespace kube-system \
      --format yaml > "k8s/secrets/$env_name/album/album-sealed.yaml"
kubectl -n monitoring get secret grafana-admin -o json \
  | kubeseal --controller-name sealed-secrets-controller --controller-namespace kube-system \
      --format yaml > "k8s/secrets/$env_name/monitoring/grafana-sealed.yaml"
kubectl -n kube-system get secrets -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml \
  > "$HOME/.local/share/kube-study/sealed-secrets-key-$env_name.yaml"
chmod 600 "$HOME/.local/share/kube-study/sealed-secrets-key-$env_name.yaml"
printf '%s\n' 'Sealed manifests written; private key backup retained outside the repository.'
