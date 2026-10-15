#!/usr/bin/env bash
# Bootstrap a fresh Ubuntu 24.04 VM as a single-node K3S host and dev workstation.
# Run on the VM as the admin user (uses sudo):  bash scripts/vm-setup.sh
# Safe to re-run; already-installed tools are skipped.
set -euo pipefail
env_name="${1:-dev}"
case "$env_name" in dev|prod) ;; *) exit 2 ;; esac

ARCH=amd64
BIN=/usr/local/bin
have() { command -v "$1" >/dev/null 2>&1; }
latest() { curl -fsSL "https://api.github.com/repos/$1/releases/latest" | jq -r .tag_name; }

sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg git jq rsync unzip make >/dev/null

# Docker Engine (image builds and docker compose for M1)
if ! have docker; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$ARCH signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release; echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin >/dev/null
  sudo usermod -aG docker "$USER"
fi

# uv (Python toolchain; venvs live on the VM, not the work PC)
have uv || curl -LsSf https://astral.sh/uv/install.sh | sh

# K3S (stable channel). Bundles kubectl, containerd, Traefik, local-path, flannel.
if ! have k3s; then
  curl -sfL https://get.k3s.io | INSTALL_K3S_CHANNEL=stable sh -s - --write-kubeconfig-mode 600
fi
mkdir -p "$HOME/.kube"
sudo install -m 600 -o "$USER" -g "$USER" /etc/rancher/k3s/k3s.yaml "$HOME/.kube/config"
# k3s' kubectl falls back to the root-only /etc/rancher/k3s/k3s.yaml unless KUBECONFIG is set
printf '%s\n' 'export KUBECONFIG=$HOME/.kube/config' \
  'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) export PATH=$HOME/.local/bin:$PATH ;; esac' \
  | sudo tee /etc/profile.d/kubeconfig.sh >/dev/null
sed -i '/^export KUBECONFIG=/d' "$HOME/.bashrc"
# ~/.bashrc returns early for non-interactive shells, so `ssh host cmd` needs it before that guard
grep -q 'kubeconfig.sh' "$HOME/.bashrc" || sed -i '1i . /etc/profile.d/kubeconfig.sh' "$HOME/.bashrc"
export KUBECONFIG="$HOME/.kube/config"

# A rebuilt cluster must load its own sealing keys before controllers start.
# The backup stays outside Git; this belongs to the first bootstrap command.
if [ -n "${SEALED_KEY_BACKUP:-}" ]; then
  [ -r "$SEALED_KEY_BACKUP" ] || { echo "Sealing key backup is unreadable" >&2; exit 1; }
  kubectl apply -f "$SEALED_KEY_BACKUP" >/dev/null
fi

# Host-based routes used by VM-side checks; Chrome uses *.localhost through SSH.
api_host="album.$env_name.local"
[ "$env_name" != prod ] || api_host=album.local
if ! getent hosts "$api_host" >/dev/null; then
  printf '127.0.0.1 %s argocd.%s.local grafana.%s.local\n' \
    "$api_host" "$env_name" "$env_name" | sudo tee -a /etc/hosts >/dev/null
fi

# Helm
have helm || curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# kubeseal (Sealed Secrets client)
if ! have kubeseal; then
  v=$(latest bitnami-labs/sealed-secrets)
  curl -fsSL "https://github.com/bitnami-labs/sealed-secrets/releases/download/${v}/kubeseal-${v#v}-linux-${ARCH}.tar.gz" \
    | sudo tar -xz -C "$BIN" kubeseal
fi

# Argo CD CLI
if ! have argocd; then
  sudo curl -fsSL -o "$BIN/argocd" "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-${ARCH}"
  sudo chmod +x "$BIN/argocd"
fi

# k6 (load testing)
if ! have k6; then
  v=$(latest grafana/k6)
  curl -fsSL "https://github.com/grafana/k6/releases/download/${v}/k6-${v}-linux-${ARCH}.tar.gz" \
    | sudo tar -xz -C "$BIN" --strip-components=1 "k6-${v}-linux-${ARCH}/k6"
fi

echo "--- installed versions"
docker --version
docker compose version
"$HOME/.local/bin/uv" --version 2>/dev/null || uv --version
k3s --version | head -1
kubectl version --client | head -1
helm version --short
kubeseal --version
argocd version --client --short
k6 version | head -1
echo "--- node"
kubectl get nodes -o wide
