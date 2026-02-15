#!/usr/bin/env bash
set -euo pipefail

# Fetches secrets from Infisical and writes a .env file in the VMs folder.

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  fi
}

require_cmd infisical

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VM_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
OUTPUT_FILE="$VM_DIR/.env"

read -r -p "Infisical Project ID: " PROJECT_ID
if [[ -z "${PROJECT_ID// }" ]]; then
  echo "ERROR: Project ID is required." >&2
  exit 1
fi

read -r -s -p "Infisical Token: " INFISICAL_TOKEN
if [[ -z "${INFISICAL_TOKEN// }" ]]; then
  echo -e "\nERROR: Token is required." >&2
  exit 1
fi

echo ""

ENV_NAME="production"
read -r -p "Environment slug [${ENV_NAME}]: " ENV_INPUT
if [[ -n "${ENV_INPUT// }" ]]; then
  ENV_NAME="$ENV_INPUT"
fi

export INFISICAL_TOKEN
export INFISICAL_DISABLE_UPDATE_CHECK=true

tmp_file=$(mktemp)

list_folders() {
  local path="$1"
  set +e
  infisical secrets folders get --path="$path" --env="$ENV_NAME" --projectId="$PROJECT_ID" --token="$INFISICAL_TOKEN"
  local status=$?
  if [[ $status -ne 0 ]]; then
    infisical secrets folders get --path="$path" --env="$ENV_NAME" --token="$INFISICAL_TOKEN"
    status=$?
  fi
  set -e
  return $status
}

read -r -p "Fetch all variables (including subfolders)? [y/N]: " FETCH_ALL
FETCH_ALL=${FETCH_ALL,,}

if [[ "$FETCH_ALL" == "y" || "$FETCH_ALL" == "yes" ]]; then
  infisical export \
    --projectId="$PROJECT_ID" \
    --env="$ENV_NAME" \
    --path="/" \
    --format=dotenv \
    --output-file="$tmp_file"
else
  echo "Available folders (root = /):"
  if ! list_folders "/"; then
    echo "WARNING: Could not list folders. You can still enter a path manually." >&2
  fi
  echo ""
  read -r -p "Enter folder path (e.g. /cloudflare): " PATH_NAME
  if [[ -z "${PATH_NAME// }" ]]; then
    echo "ERROR: Folder path is required." >&2
    exit 1
  fi
  infisical export \
    --projectId="$PROJECT_ID" \
    --env="$ENV_NAME" \
    --path="$PATH_NAME" \
    --format=dotenv \
    --output-file="$tmp_file"
fi

mv "$tmp_file" "$OUTPUT_FILE"
chmod 600 "$OUTPUT_FILE"

echo "Wrote: $OUTPUT_FILE"
