#!/usr/bin/env bash
set -euo pipefail

# Installs and runs Cloudflare Tunnel (cloudflared) via Docker Compose on the VM.
# Expects the repo to be present on the VM.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

CONFIG_PATH="$REPO_ROOT/Apps/n8n-app/ops/cloudflared/config.yml"
COMPOSE_FILE="$REPO_ROOT/Apps/n8n-app/ops/compose/cloudflared.compose.yml"
DEPS_FILE="$REPO_ROOT/Apps/n8n-app/ops/dependencies.md"

if [[ ! -f "$CONFIG_PATH" ]]; then
  echo "ERROR: Missing config at $CONFIG_PATH" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "ERROR: Missing compose file at $COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$DEPS_FILE" ]]; then
  echo "ERROR: Missing dependencies file at $DEPS_FILE" >&2
  exit 1
fi

if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" || "${CLOUDFLARE_TUNNEL_TOKEN}" == "." ]]; then
  echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required (export it in-session)." >&2
  exit 1
fi

load_deps() {
  awk -F '|' '
    NF >= 3 {
      key=$2; val=$3;
      gsub(/^[ \t]+|[ \t]+$/, "", key);
      gsub(/^[ \t]+|[ \t]+$/, "", val);
      if (key ~ /^[A-Z0-9_]+$/) {
        print key "=" val;
      }
    }
  ' "$DEPS_FILE"
}

while IFS='=' read -r key val; do
  if [[ -n "$key" && -z "${!key-}" ]]; then
    export "$key=$val"
  fi
done < <(load_deps)

# Use pinned defaults from dependencies.md if not provided.
CLOUDFLARE_IMAGE=${CLOUDFLARE_IMAGE:-cloudflare/cloudflared}
CLOUDFLARE_IMAGE_TAG=${CLOUDFLARE_IMAGE_TAG:-}
CLOUDFLARE_CONFIG_PATH=${CLOUDFLARE_CONFIG_PATH:-$CONFIG_PATH}

if [[ -z "$CLOUDFLARE_IMAGE_TAG" || "$CLOUDFLARE_IMAGE_TAG" == "TBD" ]]; then
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update Apps/n8n-app/ops/dependencies.md." >&2
  exit 1
fi

export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH

cd "$REPO_ROOT"

docker compose -f "$COMPOSE_FILE" up -d

echo "cloudflared is starting. Check logs with:"
echo "docker compose -f $COMPOSE_FILE logs -f"
