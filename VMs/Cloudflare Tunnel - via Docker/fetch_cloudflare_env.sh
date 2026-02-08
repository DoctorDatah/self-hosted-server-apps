#!/usr/bin/env bash
set -euo pipefail

# Fetches Cloudflare secrets from Infisical into the Cloudflare folder env file.

ENV_FILE="/etc/infisical.env"
OUTPUT_FILE="/home/malik/self-hosted-server-apps/VMs/Cloudflare Tunnel - via Docker/.infisical.cloudflare.env"
PROJECT_ID_FILE="/etc/infisical.project"
ENV_NAME="production"
PATH_NAME="/cloudflare"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: Missing $ENV_FILE. Add INFISICAL_TOKEN first." >&2
  exit 1
fi

if [[ ! -f "$PROJECT_ID_FILE" ]]; then
  echo "ERROR: Missing $PROJECT_ID_FILE (Infisical Project ID)." >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE"
set +a

PROJECT_ID=$(cat "$PROJECT_ID_FILE" | tr -d '[:space:]')
if [[ -z "$PROJECT_ID" ]]; then
  echo "ERROR: Project ID is empty in $PROJECT_ID_FILE" >&2
  exit 1
fi

infisical export \
  --projectId="$PROJECT_ID" \
  --env="$ENV_NAME" \
  --path="$PATH_NAME" \
  --format=dotenv \
  --output-file="$OUTPUT_FILE"

echo "Wrote: $OUTPUT_FILE"
