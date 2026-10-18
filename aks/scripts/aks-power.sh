#!/usr/bin/env bash
set -euo pipefail

readonly SUBSCRIPTION="Enterprise부문-아키텍처강화TF"
readonly RESOURCE_GROUP="rg-seonung-aks-test"
readonly CLUSTER="aks-kube-study"
readonly CONTEXT="aks-study"

usage() {
  echo "Usage: bash aks/scripts/aks-power.sh stop|start" >&2
}

if [[ $# != 1 || ( $1 != stop && $1 != start ) ]]; then
  usage
  exit 2
fi
action=$1

require_quiet_namespace() {
  local namespace=$1
  local environment=${namespace#album-}
  for application in "root-$environment" "$namespace"; do
    if kubectl --context "$CONTEXT" -n argocd get application "$application" >/dev/null 2>&1; then
      local automated
      automated=$(kubectl --context "$CONTEXT" -n argocd get application "$application" \
        -o jsonpath='{.spec.syncPolicy.automated}')
      if [[ -n $automated ]]; then
        echo "Refusing to stop: pause Argo CD automated sync for $application first." >&2
        return 1
      fi
    fi
  done
  if ! kubectl --context "$CONTEXT" get namespace "$namespace" >/dev/null 2>&1; then
    return 0
  fi
  for deployment in api frontend worker; do
    local replicas
    replicas=$(kubectl --context "$CONTEXT" -n "$namespace" get deployment "$deployment" \
      -o jsonpath='{.spec.replicas}')
    if [[ $replicas != 0 ]]; then
      echo "Refusing to stop: $namespace/$deployment has desired replicas ${replicas:-unset}." >&2
      return 1
    fi
  done
  if kubectl --context "$CONTEXT" -n "$namespace" get hpa api >/dev/null 2>&1; then
    echo "Refusing to stop: remove or disable the $namespace API HPA first." >&2
    return 1
  fi
  echo "Verified $namespace API, frontend, and worker are scaled to zero."
}

wait_for_aks_state() {
  local wanted_power=$1
  local wanted_provisioning=$2
  for _ in $(seq 1 180); do
    local power provisioning
    power=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
      --name "$CLUSTER" --query powerState.code -o tsv)
    provisioning=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
      --name "$CLUSTER" --query provisioningState -o tsv)
    if [[ $power == "$wanted_power" && $provisioning == "$wanted_provisioning" ]]; then
      echo "AKS state: power=$power provisioning=$provisioning"
      return 0
    fi
    sleep 10
  done
  echo "Timed out waiting for AKS power=$wanted_power provisioning=$wanted_provisioning." >&2
  return 1
}

identity=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER" --query name -o tsv)
if [[ $identity != "$CLUSTER" ]]; then
  echo "The selected subscription/resource group did not resolve to the expected AKS cluster." >&2
  exit 1
fi
current_context=$(kubectl config current-context)
if [[ $current_context != "$CONTEXT" ]]; then
  echo "Kubernetes current context must be $CONTEXT; no context is changed." >&2
  exit 1
fi
cluster_fqdn=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER" --query fqdn -o tsv)
context_server=$(kubectl config view --context "$CONTEXT" --minify \
  -o jsonpath='{.clusters[0].cluster.server}')
if [[ -z $cluster_fqdn || $context_server != *"$cluster_fqdn"* ]]; then
  echo "Kubernetes context $CONTEXT does not point to the selected AKS endpoint." >&2
  exit 1
fi

power=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
  --name "$CLUSTER" --query powerState.code -o tsv)
if [[ $action == stop ]]; then
  if [[ $power == Stopped ]]; then
    wait_for_aks_state Stopped Succeeded
    exit 0
  fi
  if [[ $power != Running ]]; then
    echo "Refusing to stop AKS in unexpected power state: $power" >&2
    exit 1
  fi
  require_quiet_namespace album-dev
  require_quiet_namespace album-prod
  echo "Stopping AKS $CLUSTER in $RESOURCE_GROUP ($SUBSCRIPTION)."
  az aks stop --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" --name "$CLUSTER"
  wait_for_aks_state Stopped Succeeded
else
  if [[ $power == Running ]]; then
    wait_for_aks_state Running Succeeded
  elif [[ $power == Stopped ]]; then
    echo "Starting AKS $CLUSTER in $RESOURCE_GROUP ($SUBSCRIPTION)."
    az aks start --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" --name "$CLUSTER"
    wait_for_aks_state Running Succeeded
  else
    echo "Refusing to start AKS in unexpected power state: $power" >&2
    exit 1
  fi
  expected=$(az aks show --subscription "$SUBSCRIPTION" --resource-group "$RESOURCE_GROUP" \
    --name "$CLUSTER" --query agentPoolProfiles[0].count -o tsv)
  for _ in $(seq 1 60); do
    ready=$(kubectl --context "$CONTEXT" get nodes -o json | python3 -c \
      'import json,sys; data=json.load(sys.stdin); print(sum(condition["type"]=="Ready" and condition["status"]=="True" for node in data["items"] for condition in node["status"]["conditions"]))')
    if [[ $ready -ge $expected ]]; then
      echo "Ready nodes: $ready/$expected"
      exit 0
    fi
    sleep 10
  done
  echo "AKS is Running but timed out waiting for Ready nodes." >&2
  exit 1
fi
