#!/usr/bin/env bash
set -euo pipefail

# Shows cloudflared logs with pinned defaults from requirements.txt (no manual exports).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

CONFIG_PATH="$SCRIPT_DIR/config.yml"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
DEPS_FILE="$SCRIPT_DIR/requirements.txt"

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

while IFS='=' read -r key val; do
  [[ -z "${key// }" || "${key:0:1}" == "#" ]] && continue
  key="$(echo "$key" | xargs)"
  val="$(echo "${val-}" | xargs)"
  if [[ -n "$key" && -z "${!key-}" ]]; then
    export "$key=$val"
  fi
done < "$DEPS_FILE"

CLOUDFLARE_IMAGE=${CLOUDFLARE_IMAGE:-cloudflare/cloudflared}
CLOUDFLARE_IMAGE_TAG=${CLOUDFLARE_IMAGE_TAG:-}
CLOUDFLARE_CONFIG_PATH=${CLOUDFLARE_CONFIG_PATH:-$CONFIG_PATH}

if [[ -z "$CLOUDFLARE_IMAGE_TAG" || "$CLOUDFLARE_IMAGE_TAG" == "TBD" ]]; then
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update VMs/Cloudflare Tunnel (via Docker)/requirements.txt." >&2
  exit 1
fi

export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH

docker compose -f "$COMPOSE_FILE" logs -f
