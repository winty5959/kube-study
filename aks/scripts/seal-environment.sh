#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(cd "$script_dir/.." && pwd)"
kubeconfig="${KUBECONFIG:-$project_dir/infra/azure/local/kubeconfig}"
kube_context="${KUBE_CONTEXT:-aks-study}"
kubectl_cmd=(kubectl --kubeconfig "$kubeconfig" --context "$kube_context")
secure_dir="${HOME}/.local/share/kube-study"
credential_file="$secure_dir/aks-dev-secrets.env"
key_backup="$secure_dir/sealed-secrets-key-aks-dev.yaml"
key_selector='sealedsecrets.bitnami.com/sealed-secrets-key'

environment="${1:?usage: seal-environment.sh dev}"
[[ "$environment" == dev ]] || { echo 'AKS currently supports dev secrets only' >&2; exit 2; }

umask 077
mkdir -p "$secure_dir"
chmod 700 "$secure_dir"

if [[ ! -f "$credential_file" ]]; then
  credential_tmp="$(mktemp "$secure_dir/aks-dev-secrets.XXXXXX")"
  trap 'rm -f "$credential_tmp"' EXIT
  {
    printf 'POSTGRES_PASSWORD=%s\n' "$(openssl rand -hex 32)"
    printf 'S3_ACCESS_KEY=%s\n' "$(openssl rand -hex 10)"
    printf 'S3_SECRET_KEY=%s\n' "$(openssl rand -hex 32)"
    printf 'GRAFANA_ADMIN_PASSWORD=%s\n' "$(openssl rand -hex 32)"
  } > "$credential_tmp"
  chmod 600 "$credential_tmp"
  mv "$credential_tmp" "$credential_file"
  trap - EXIT
fi
chmod 600 "$credential_file"
POSTGRES_PASSWORD=''
S3_ACCESS_KEY=''
S3_SECRET_KEY=''
GRAFANA_ADMIN_PASSWORD=''
while IFS='=' read -r key value; do
  case "$key" in
    POSTGRES_PASSWORD) POSTGRES_PASSWORD="$value" ;;
    S3_ACCESS_KEY) S3_ACCESS_KEY="$value" ;;
    S3_SECRET_KEY) S3_SECRET_KEY="$value" ;;
    GRAFANA_ADMIN_PASSWORD) GRAFANA_ADMIN_PASSWORD="$value" ;;
    *) echo 'AKS secret file contains an unsupported key' >&2; exit 1 ;;
  esac
done < "$credential_file"
for value in "$POSTGRES_PASSWORD" "$S3_ACCESS_KEY" "$S3_SECRET_KEY" "$GRAFANA_ADMIN_PASSWORD"; do
  [[ "$value" =~ ^[0-9a-f]+$ ]] || { echo 'AKS secret file has an invalid value format' >&2; exit 1; }
done

task_tmp="$(mktemp -d)"
trap 'rm -rf "$task_tmp"' EXIT
"${kubectl_cmd[@]}" get secrets -n kube-system -l "$key_selector" -o yaml > "$task_tmp/key-bundle.yaml"
[[ -s "$task_tmp/key-bundle.yaml" ]] || { echo 'No SealedSecrets key is available in AKS' >&2; exit 1; }
"${kubectl_cmd[@]}" get secrets -n kube-system -l "$key_selector" -o json > "$task_tmp/key-bundle.json"
ruby -e 'require "json"; require "base64"; items = JSON.parse(File.read(ARGV.fetch(0))).fetch("items"); key = items.max_by { |item| item.dig("metadata", "creationTimestamp") }; abort "SealedSecrets certificate is unavailable" unless key; print Base64.decode64(key.dig("data", "tls.crt").to_s)' "$task_tmp/key-bundle.json" > "$task_tmp/controller.crt"
[[ -s "$task_tmp/controller.crt" ]] || { echo 'SealedSecrets certificate is unavailable' >&2; exit 1; }

key_fingerprint() {
  ruby -e 'require "yaml"; require "base64"; require "digest"; doc = YAML.load_file(ARGV.fetch(0)); items = doc["items"] || [doc]; keys = items.sort_by { |item| item.dig("metadata", "name") }.map { |item| [item.dig("metadata", "name"), Base64.decode64(item.dig("data", "tls.key").to_s)] }; abort "SealedSecrets key data is incomplete" if keys.empty? || keys.any? { |name, key| name.nil? || key.empty? }; print Digest::SHA256.hexdigest(keys.map { |name, key| name + "\0" + key }.join("\0"))' "$1"
}

if [[ -e "$key_backup" ]]; then
  live_fingerprint="$(key_fingerprint "$task_tmp/key-bundle.yaml")"
  saved_fingerprint="$(key_fingerprint "$key_backup")"
  [[ "$live_fingerprint" == "$saved_fingerprint" ]] || {
    echo 'The AKS sealing key differs from the saved backup; refusing to overwrite either copy' >&2
    exit 1
  }
else
  install -m 600 "$task_tmp/key-bundle.yaml" "$key_backup"
fi

"${kubectl_cmd[@]}" create namespace album-dev --dry-run=client -o yaml | "${kubectl_cmd[@]}" apply -f - >/dev/null
"${kubectl_cmd[@]}" create namespace monitoring --dry-run=client -o yaml | "${kubectl_cmd[@]}" apply -f - >/dev/null

"${kubectl_cmd[@]}" create secret generic album-secrets -n album-dev \
  --from-literal="POSTGRES_PASSWORD=$POSTGRES_PASSWORD" \
  --from-literal="S3_ACCESS_KEY=$S3_ACCESS_KEY" \
  --from-literal="S3_SECRET_KEY=$S3_SECRET_KEY" --dry-run=client -o yaml \
  | kubeseal --cert "$task_tmp/controller.crt" --scope strict --format yaml \
      > "$project_dir/k8s/secrets/dev/album/album-sealed.yaml"

"${kubectl_cmd[@]}" create secret generic grafana-admin -n monitoring \
  --from-literal=admin-user=admin --from-literal="admin-password=$GRAFANA_ADMIN_PASSWORD" \
  --dry-run=client -o yaml \
  | kubeseal --cert "$task_tmp/controller.crt" --scope strict --format yaml \
      > "$project_dir/k8s/secrets/dev/monitoring/grafana-sealed.yaml"

"${kubectl_cmd[@]}" apply -k "$project_dir/k8s/secrets/dev/album" >/dev/null
"${kubectl_cmd[@]}" apply -k "$project_dir/k8s/secrets/dev/monitoring" >/dev/null
"${kubectl_cmd[@]}" wait --for=condition=Synced sealedsecret/album-secrets -n album-dev --timeout=120s >/dev/null
"${kubectl_cmd[@]}" wait --for=condition=Synced sealedsecret/grafana-admin -n monitoring --timeout=120s >/dev/null

for secret_key in POSTGRES_PASSWORD S3_ACCESS_KEY S3_SECRET_KEY; do
  encoded="$("${kubectl_cmd[@]}" get secret album-secrets -n album-dev -o "jsonpath={.data.$secret_key}")"
  [[ -n "$encoded" ]] || { echo "Required album key is missing: $secret_key" >&2; exit 1; }
done
for secret_key in admin-user admin-password; do
  encoded="$("${kubectl_cmd[@]}" get secret grafana-admin -n monitoring -o "jsonpath={.data.$secret_key}")"
  [[ -n "$encoded" ]] || { echo "Required Grafana key is missing: $secret_key" >&2; exit 1; }
done

printf '%s\n' 'AKS dev credentials sealed and decrypted; AKS-only key backup verified outside the repository.'
