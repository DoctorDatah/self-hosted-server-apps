#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

COMPOSE_FILE="$(vmcx_param_get compose_file "$SCRIPT_DIR/templates/docker-compose.yml")"
ACTION="$(vmcx_param_get action up)"
MODE="app_access"

if [[ -z "$COMPOSE_FILE" ]]; then
  echo "--compose-file is required" >&2
  exit 1
fi
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi
if [[ "$ACTION" != "up" && "$ACTION" != "down" ]]; then
  echo "Invalid action: $ACTION" >&2
  exit 1
fi

vmcx_require_cmd docker

echo "[cloudflare_app_access] target=${VMCX_TARGET_ID:-unknown} mode=${VMCX_EXEC_MODE:-unknown} cf_mode=$MODE action=$ACTION"

if [[ "$ACTION" == "up" ]]; then
  docker compose -f "$COMPOSE_FILE" up -d
else
  docker compose -f "$COMPOSE_FILE" down
fi

echo "[cloudflare_app_access] complete"
