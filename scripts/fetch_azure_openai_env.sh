#!/usr/bin/env bash
# Write the team's Azure OpenAI endpoint and key from Key Vault into the git-ignored .env.
# Usage: az login && scripts/fetch_azure_openai_env.sh [team-number]
set -euo pipefail
TEAM="${1:-12}"
RG="rg-hack-team${TEAM}-swc"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

KV="$(az keyvault list -g "$RG" --query "[0].name" -o tsv)"
[ -n "$KV" ] || { echo "No Key Vault found in $RG. Are you in grp-hack-team${TEAM}?" >&2; exit 1; }

ENDPOINT="$(az keyvault secret show --vault-name "$KV" -n azure-openai-endpoint --query value -o tsv)"
KEY="$(az keyvault secret show --vault-name "$KV" -n azure-openai-key --query value -o tsv)"

umask 077
cat > "$ROOT/.env" <<ENV
AZURE_OPENAI_ENDPOINT=$ENDPOINT
AZURE_OPENAI_API_KEY=$KEY
AZURE_OPENAI_DEPLOYMENT=gpt-4.1-mini
AZURE_OPENAI_API_VERSION=2024-10-21
ENV
echo "Wrote $ROOT/.env from Key Vault $KV (key not printed)."
