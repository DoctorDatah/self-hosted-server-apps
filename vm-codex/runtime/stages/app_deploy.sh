#!/usr/bin/env bash
set -euo pipefail

COMPOSE_FILE=""
SECTION="all"

usage() {
  cat <<'USAGE'
Usage: app_deploy.sh --compose-file <path> [--section infra|app|post|all]
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --compose-file)
      shift
      COMPOSE_FILE="${1-}"
      ;;
    --section)
      shift
      SECTION="${1-}"
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

if [[ -z "$COMPOSE_FILE" ]]; then
  echo "--compose-file is required" >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  echo "Compose file not found: $COMPOSE_FILE" >&2
  exit 1
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is required" >&2
  exit 1
fi

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
