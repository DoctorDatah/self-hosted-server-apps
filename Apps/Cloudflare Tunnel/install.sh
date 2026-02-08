#!/usr/bin/env bash
set -euo pipefail

# Installs Docker (if missing) and runs Cloudflare Tunnel (cloudflared) via Docker Compose on the VM.
# Expects the repo to be present on the VM.

show_usage() {
  cat <<'USAGE'
Usage: ./install.sh [--skip-docker] [--pull] [--down]

Requires:
  - Repo cloned on the VM
  - Apps/cloudflare/config.yml
  - Apps/cloudflare/docker-compose.yml
  - Apps/cloudflare/requirements.txt

Flags:
  --skip-docker  Skip Docker install checks/installation
  --pull         Pull latest images before starting
  --down         Stop the tunnel instead of starting
USAGE
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  show_usage
  exit 0
fi

skip_docker=false
pull=false
down=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip-docker)
      skip_docker=true
      ;;
    --pull)
      pull=true
      ;;
    --down)
      down=true
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      show_usage
      exit 1
      ;;
  esac
  shift
done

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

CONFIG_PATH="$SCRIPT_DIR/config.yml"
GENERATED_CONFIG_PATH="$SCRIPT_DIR/config.generated.yml"
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
  echo "ERROR: Missing requirements file at $DEPS_FILE" >&2
  exit 1
fi

if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" || "${CLOUDFLARE_TUNNEL_TOKEN}" == "." ]]; then
  echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required (export it in-session)." >&2
  exit 1
fi

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: $1 is required. Install it and rerun." >&2
    exit 1
  }
}

install_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    return 0
  fi

  if [[ $EUID -ne 0 ]]; then
    echo "ERROR: Docker is missing and install requires root. Re-run with sudo or install Docker manually." >&2
    exit 1
  fi

  require_cmd apt-get
  require_cmd curl
  require_cmd gpg

  echo "Installing Docker Engine + Compose plugin..."
  apt-get update
  apt-get install -y ca-certificates curl gnupg
  install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  chmod a+r /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
    $(. /etc/os-release && echo \"$VERSION_CODENAME\") stable" | \
    tee /etc/apt/sources.list.d/docker.list > /dev/null
  apt-get update
  apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
}

if [[ "$skip_docker" == "false" ]]; then
  install_docker
fi

echo
read -r -p "Select app tags for tunnel config now? [Y/n]: " PICK_TAGS
PICK_TAGS="${PICK_TAGS:-Y}"
if [[ "$PICK_TAGS" =~ ^[Yy]$ ]]; then
  mapfile -t TAGS < <(awk '/^\s*# \[[^/].*\]/{gsub(/^\s*# \[/,""); gsub(/\].*$/,""); print}' "$CONFIG_PATH")
  if [[ ${#TAGS[@]} -eq 0 ]]; then
    echo "No tags found in $CONFIG_PATH." >&2
    exit 1
  fi

  echo "Available tags:"
  for t in "${TAGS[@]}"; do
    echo "- ${t}"
  done
  echo
  read -r -p "Select tags (comma-separated, e.g. coolify,n8n): " SELECTED_RAW
  SELECTED_RAW="${SELECTED_RAW// /}"
  if [[ -z "${SELECTED_RAW}" ]]; then
    echo "No tags selected."
    exit 1
  fi

  awk -v selected_list="${SELECTED_RAW}" '
    BEGIN {
      split(selected_list, arr, ",");
      for (i in arr) { sel[arr[i]] = 1; }
      in_block = 0; emit = 1;
    }
    /^\s*# \[[^/].*\]/ {
      tag=$0; sub(/^\s*# \[/, "", tag); sub(/\].*$/, "", tag);
      in_block = 1;
      emit = (tag in sel);
      next;
    }
    /^\s*# \[\/.*\]/ {
      in_block = 0;
      emit = 1;
      next;
    }
    {
      if (!in_block || emit) { print; }
    }
  ' "$CONFIG_PATH" > "$GENERATED_CONFIG_PATH"
fi

while IFS='=' read -r key val; do
  [[ -z "${key// }" || "${key:0:1}" == "#" ]] && continue
  key="$(echo "$key" | xargs)"
  val="$(echo "${val-}" | xargs)"
  if [[ -n "$key" && -z "${!key-}" ]]; then
    export "$key=$val"
  fi
done < "$DEPS_FILE"

# Use pinned defaults from requirements.txt if not provided.
CLOUDFLARE_IMAGE=${CLOUDFLARE_IMAGE:-cloudflare/cloudflared}
CLOUDFLARE_IMAGE_TAG=${CLOUDFLARE_IMAGE_TAG:-}

if [[ -f "$GENERATED_CONFIG_PATH" ]]; then
  CLOUDFLARE_CONFIG_PATH=${CLOUDFLARE_CONFIG_PATH:-$GENERATED_CONFIG_PATH}
else
  CLOUDFLARE_CONFIG_PATH=${CLOUDFLARE_CONFIG_PATH:-$CONFIG_PATH}
fi

if [[ -z "$CLOUDFLARE_IMAGE_TAG" || "$CLOUDFLARE_IMAGE_TAG" == "TBD" ]]; then
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update Apps/cloudflare/requirements.txt." >&2
  exit 1
fi

export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH

cd "$REPO_ROOT"

if [[ "$down" == "true" ]]; then
  docker compose -f "$COMPOSE_FILE" down
  exit 0
fi

if [[ "$pull" == "true" ]]; then
  docker compose -f "$COMPOSE_FILE" pull
fi

docker compose -f "$COMPOSE_FILE" up -d

echo "cloudflared is starting. Check logs with:"
echo "docker compose -f $COMPOSE_FILE logs -f"
