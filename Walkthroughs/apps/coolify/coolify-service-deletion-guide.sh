#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Coolify service cleanup helper (Docker)

Usage:
  ./coolify-service-cleanup.sh [options]

Options:
  --list-volumes                 List docker volumes
  --inspect-volume <name>        Inspect a docker volume
  --remove-volume <name>         Remove a specific docker volume
  --prune-volumes                Remove unused docker volumes only
  --prune-docker                 Remove unused containers, images, networks, and volumes
  -y, --yes                      Skip confirmation prompts
  -h, --help                     Show this help

Examples:
  ./coolify-service-cleanup.sh --list-volumes
  ./coolify-service-cleanup.sh --inspect-volume coolify_pgdata
  ./coolify-service-cleanup.sh --remove-volume coolify_pgdata
  ./coolify-service-cleanup.sh --prune-volumes
  ./coolify-service-cleanup.sh --prune-docker -y
EOF
}

confirm() {
  local prompt="$1"
  read -rp "$prompt (y/N): " ans
  [[ ${ans,,} == "y" ]]
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: $1 is required. Install it and rerun." >&2
    exit 1
  }
}

auto_approve=false
action=""
volume_name=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --list-volumes)
      action="list_volumes"
      ;;
    --inspect-volume)
      [[ $# -lt 2 ]] && { echo "Missing value for --inspect-volume" >&2; exit 1; }
      action="inspect_volume"
      volume_name="$2"
      shift
      ;;
    --remove-volume)
      [[ $# -lt 2 ]] && { echo "Missing value for --remove-volume" >&2; exit 1; }
      action="remove_volume"
      volume_name="$2"
      shift
      ;;
    --prune-volumes)
      action="prune_volumes"
      ;;
    --prune-docker)
      action="prune_docker"
      ;;
    -y|--yes)
      auto_approve=true
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

if [[ -z "$action" ]]; then
  usage
  exit 1
fi

require_cmd docker

case "$action" in
  list_volumes)
    docker volume ls
    ;;
  inspect_volume)
    docker volume inspect "$volume_name"
    ;;
  remove_volume)
    if [[ $auto_approve == false ]]; then
      confirm "Remove volume '$volume_name'? This cannot be undone." || exit 0
    fi
    docker volume rm "$volume_name"
    ;;
  prune_volumes)
    if [[ $auto_approve == false ]]; then
      confirm "Prune unused volumes? This deletes data not used by any container." || exit 0
    fi
    docker volume prune -f
    ;;
  prune_docker)
    if [[ $auto_approve == false ]]; then
      confirm "Prune ALL unused Docker data (images, containers, networks, volumes)?" || exit 0
    fi
    docker system prune -a -f --volumes
    ;;
esac
