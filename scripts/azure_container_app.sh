#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Prepare an Azure Container Apps create command. This script makes no Azure
requests unless --execute is passed.

Required environment variables:
  HTC_SUBSCRIPTION_ID  Subscription to charge
  HTC_RESOURCE_GROUP    Existing resource group
  HTC_ENVIRONMENT       Existing Container Apps environment with Consumption profile
  HTC_APP_NAME          New container app name
  HTC_IMAGE             Already-published, pullable container image (immutable tag/digest)

Usage: scripts/azure_container_app.sh [--execute]
EOF
}

if (( $# > 1 )); then
  usage >&2
  exit 2
fi

case "${1:-}" in
  --help|-h) usage; exit 0 ;;
  "") ;;
  --execute) ;;
  *) usage >&2; exit 2 ;;
esac

required=(HTC_SUBSCRIPTION_ID HTC_RESOURCE_GROUP HTC_ENVIRONMENT HTC_APP_NAME HTC_IMAGE)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    printf 'Missing %s\n' "$name" >&2
    usage >&2
    exit 2
  fi
done

command=(
  az containerapp create
  --subscription "$HTC_SUBSCRIPTION_ID"
  --resource-group "$HTC_RESOURCE_GROUP"
  --environment "$HTC_ENVIRONMENT"
  --name "$HTC_APP_NAME"
  --image "$HTC_IMAGE"
  --workload-profile-name Consumption
  --ingress external
  --target-port 8000
  --cpu 0.5
  --memory 1.0Gi
  --min-replicas 0
  --max-replicas 1
  --revisions-mode single
  --query properties.configuration.ingress.fqdn
  --output tsv
)

printf 'Proposed Azure command:\n'
printf '%q ' "${command[@]}"
printf '\n'

if [[ "${1:-}" != --execute ]]; then
  printf 'Preview only. No Azure request was made.\n'
  exit 0
fi

command -v az >/dev/null || { printf 'Azure CLI is required.\n' >&2; exit 1; }
active_subscription="$(az account show --query id --output tsv)"
if [[ "$active_subscription" != "$HTC_SUBSCRIPTION_ID" ]]; then
  printf 'Active subscription differs from HTC_SUBSCRIPTION_ID; select it explicitly before deploying.\n' >&2
  exit 1
fi

"${command[@]}"
