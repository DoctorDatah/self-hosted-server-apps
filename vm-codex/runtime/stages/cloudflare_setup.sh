#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=""
MODE=""
ACTION="up"

usage() {
  cat <<'USAGE'
Usage: cloudflare_setup.sh --compose-file <path> --mode vm_access|app_access [--action up|down]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      shift
      COMPOSE_FILE="${1-}"
      ;;
    --mode)
      shift
      MODE="${1-}"
      ;;
    --action)
      shift
      ACTION="${1-}"
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

if [[ -z "$COMPOSE_FILE" || -z "$MODE" ]]; then
  echo "--compose-file and --mode are required" >&2
  exit 1
fi
if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi
if [[ "$MODE" != "vm_access" && "$MODE" != "app_access" ]]; then
  echo "Invalid mode: $MODE" >&2
  exit 1
fi
if [[ "$ACTION" != "up" && "$ACTION" != "down" ]]; then
  echo "Invalid action: $ACTION" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required" >&2
  exit 1
fi

if [[ "$ACTION" == "up" ]]; then
  docker compose -f "$COMPOSE_FILE" up -d
else
  docker compose -f "$COMPOSE_FILE" down
fi
