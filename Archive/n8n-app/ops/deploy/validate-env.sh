#!/usr/bin/env bash
set -euo pipefail

required_vars=(
  CLOUDFLARE_IMAGE
  CLOUDFLARE_IMAGE_TAG
  CLOUDFLARE_CONFIG_PATH
  CLOUDFLARE_TUNNEL_TOKEN
  N8N_IMAGE
  N8N_IMAGE_TAG
  POSTGRES_IMAGE
  POSTGRES_IMAGE_TAG
  POSTGRES_DB
  POSTGRES_USER
  POSTGRES_PASSWORD
  N8N_ENCRYPTION_KEY
  N8N_HOST
  N8N_PROTOCOL
  N8N_PORT
  WEBHOOK_URL
  N8N_EDITOR_BASE_URL
  N8N_DATA_PATH
  POSTGRES_DATA_PATH
)

missing=()
for var in "${required_vars[@]}"; do
  if [[ -z "${!var-}" || "${!var}" == "TBD" ]]; then
    missing+=("$var")
  fi
done

if (( ${#missing[@]} > 0 )); then
  echo "Missing required environment variables:" >&2
  printf ' - %s\n' "${missing[@]}" >&2
  exit 1
fi
