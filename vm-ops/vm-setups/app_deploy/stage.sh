#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

COMPOSE_FILE="$(vmcx_param_get compose_file docker-compose.yml)"
SECTION="$(vmcx_param_get section all)"

if [[ ! -f "$COMPOSE_FILE" && -f "$SCRIPT_DIR/templates/docker-compose.yml" ]]; then
  COMPOSE_FILE="$SCRIPT_DIR/templates/docker-compose.yml"
fi

if [[ -z "$COMPOSE_FILE" ]]; then
  echo "--compose-file is required" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

vmcx_require_cmd docker

echo "[app_deploy] target=${VMCX_TARGET_ID:-unknown} mode=${VMCX_EXEC_MODE:-unknown}"
echo "[app_deploy] compose_file=$COMPOSE_FILE section=$SECTION"

case "$SECTION" in
  infra)
    docker compose -f "$COMPOSE_FILE" pull
    ;;
  app)
    docker compose -f "$COMPOSE_FILE" up -d
    ;;
  post)
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  all)
    docker compose -f "$COMPOSE_FILE" pull
    docker compose -f "$COMPOSE_FILE" up -d
    docker compose -f "$COMPOSE_FILE" ps
    ;;
  *)
    echo "Invalid section: $SECTION" >&2
    exit 1
    ;;
esac

echo "[app_deploy] complete"
