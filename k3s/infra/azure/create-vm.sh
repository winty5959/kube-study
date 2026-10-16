#!/usr/bin/env bash
# Create a K3S host VM on Azure for the given environment (dev | prod).
# Usage: infra/azure/create-vm.sh dev
#
# The SSH public key path and the allowed source IP are resolved at runtime
# so that no key material or personal IP is stored in the repository.
set -euo pipefail

ENV="${1:?usage: $0 <dev|prod>}"
case "$ENV" in
  dev)  SUBNET_PREFIX="10.20.1.0/24" ;;
  prod) SUBNET_PREFIX="10.20.2.0/24" ;;
  *) echo "env must be dev or prod" >&2; exit 1 ;;
esac

SUBSCRIPTION="${SUBSCRIPTION:-AX사업부문-인프라아키텍처팀}"
LOCATION="${LOCATION:-koreacentral}"
RG="${RG:-rg-seonung-kube-study}"
VM_SIZE="${VM_SIZE:-Standard_B4as_v2}"
IMAGE="${IMAGE:-Canonical:ubuntu-24_04-lts:server:latest}"
DISK_SKU="${DISK_SKU:-StandardSSD_LRS}"
DISK_GB="${DISK_GB:-64}"
ADMIN_USER="${ADMIN_USER:-azureuser}"
SSH_PUBKEY="${SSH_PUBKEY:-$HOME/.ssh/kube-study.pub}"
# 18:00 KST == 09:00 UTC
SHUTDOWN_UTC="${SHUTDOWN_UTC:-0900}"
ALLOWED_IP="${ALLOWED_IP:-$(curl -fsS https://api.ipify.org)}"

VNET="vnet-kube-study"
NAME="vm-kube-${ENV}"
NSG="nsg-kube-${ENV}"
PIP="pip-kube-${ENV}"
NIC="nic-kube-${ENV}"
SUBNET="snet-${ENV}"
TAGS=(project=kube-study env="$ENV")

az account set --subscription "$SUBSCRIPTION"
export AZURE_CORE_ONLY_SHOW_ERRORS=true

az group create -n "$RG" -l "$LOCATION" --tags "${TAGS[@]}" -o none

az network vnet create -g "$RG" -n "$VNET" -l "$LOCATION" \
  --address-prefixes 10.20.0.0/16 --tags "${TAGS[@]}" -o none

az network nsg create -g "$RG" -n "$NSG" -l "$LOCATION" --tags "${TAGS[@]}" -o none
az network nsg rule create -g "$RG" --nsg-name "$NSG" -n allow-ssh-workpc \
  --priority 100 --direction Inbound --access Allow --protocol Tcp \
  --source-address-prefixes "${ALLOWED_IP}/32" --destination-port-ranges 22 -o none

az network vnet subnet create -g "$RG" --vnet-name "$VNET" -n "$SUBNET" \
  --address-prefixes "$SUBNET_PREFIX" --network-security-group "$NSG" -o none

az network public-ip create -g "$RG" -n "$PIP" -l "$LOCATION" \
  --sku Standard --allocation-method Static --tags "${TAGS[@]}" -o none

az network nic create -g "$RG" -n "$NIC" -l "$LOCATION" \
  --vnet-name "$VNET" --subnet "$SUBNET" --public-ip-address "$PIP" \
  --tags "${TAGS[@]}" -o none

if ! az vm show -g "$RG" -n "$NAME" -o none 2>/dev/null; then
  az vm create -g "$RG" -n "$NAME" -l "$LOCATION" \
    --size "$VM_SIZE" --image "$IMAGE" --nics "$NIC" \
    --os-disk-size-gb "$DISK_GB" --storage-sku "$DISK_SKU" \
    --admin-username "$ADMIN_USER" --ssh-key-values "$SSH_PUBKEY" \
    --tags "${TAGS[@]}" -o none
fi

az vm auto-shutdown -g "$RG" -n "$NAME" --time "$SHUTDOWN_UTC" -o none

IP=$(az network public-ip show -g "$RG" -n "$PIP" --query ipAddress -o tsv)
echo "VM ${NAME} ready: ssh -i ${SSH_PUBKEY%.pub} ${ADMIN_USER}@${IP}"
