#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

DEPS_FILE="$REPO_ROOT/Apps/n8n-app/ops/dependencies.md"
COMPOSE_DIR="$REPO_ROOT/Apps/n8n-app/ops/compose"
VALIDATE_ENV="$REPO_ROOT/Apps/n8n-app/ops/deploy/validate-env.sh"

if [[ ! -f "$DEPS_FILE" ]]; then
  echo "ERROR: dependencies file not found at $DEPS_FILE" >&2
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

export CLOUDFLARE_CONFIG_PATH="${CLOUDFLARE_CONFIG_PATH:-$REPO_ROOT/Apps/n8n-app/ops/cloudflared/config.yml}"
export N8N_DATA_PATH="${N8N_DATA_PATH:-/var/lib/n8n}"
export POSTGRES_DATA_PATH="${POSTGRES_DATA_PATH:-/var/lib/n8n/postgres}"

if [[ ! -x "$VALIDATE_ENV" ]]; then
  echo "ERROR: validate-env.sh is missing or not executable: $VALIDATE_ENV" >&2
  exit 1
fi

"$VALIDATE_ENV"

mkdir -p "$N8N_DATA_PATH" "$POSTGRES_DATA_PATH"

cd "$REPO_ROOT"

docker compose \
  -f "$COMPOSE_DIR/cloudflared.compose.yml" \
  -f "$COMPOSE_DIR/n8n.compose.yml" \
  up -d

