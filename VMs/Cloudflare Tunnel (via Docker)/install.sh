#!/usr/bin/env bash
set -euo pipefail

# Installs Docker (if missing) and runs Cloudflare Tunnel (cloudflared) via Docker Compose on the VM.
# Expects the repo to be present on the VM.

show_usage() {
  cat <<'USAGE'
Usage: ./install.sh [--skip-docker] [--pull] [--down]

Requires:
  - Repo cloned on the VM
  - VMs/Cloudflare Tunnel (via Docker)/config.yml
  - VMs/Cloudflare Tunnel (via Docker)/docker-compose.yml
  - VMs/Cloudflare Tunnel (via Docker)/requirements.txt

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
mapfile -t TAGS < <(awk '/^[[:space:]]*# \[[^/].*\]/{gsub(/^[[:space:]]*# \[/,""); gsub(/\].*$/,""); print}' "$CONFIG_PATH")
if [[ ${#TAGS[@]} -eq 0 ]]; then
  echo "No tags found in $CONFIG_PATH." >&2
  exit 1
fi

echo "Available tags:"
for t in "${TAGS[@]}"; do
  echo "- ${t}"
done

while true; do
  echo
  read -r -p "Select tags (comma-separated, e.g. app-main,app-ws): " SELECTED_RAW
  SELECTED_RAW="${SELECTED_RAW// /}"
  if [[ -z "${SELECTED_RAW}" ]]; then
    echo "Please select at least one tag."
    continue
  fi
  break
done

IFS=',' read -r FIRST_TAG _ <<< "$SELECTED_RAW"
DEFAULT_APP_NETWORK=""
case "$FIRST_TAG" in
  coolify)
    DEFAULT_APP_NETWORK="coolify"
    ;;
  n8n)
    DEFAULT_APP_NETWORK="n8n"
    ;;
esac

if [[ "$SELECTED_RAW" == *","* ]]; then
  echo "Note: Multiple tags selected. Ensure all services are reachable on the same network."
fi

echo
read -r -p "Docker network for target app [${DEFAULT_APP_NETWORK}]: " CLOUDFLARE_APP_NETWORK
CLOUDFLARE_APP_NETWORK="${CLOUDFLARE_APP_NETWORK// /}"
if [[ -z "$CLOUDFLARE_APP_NETWORK" ]]; then
  CLOUDFLARE_APP_NETWORK="$DEFAULT_APP_NETWORK"
fi

if [[ -z "$CLOUDFLARE_APP_NETWORK" ]]; then
  echo "ERROR: CLOUDFLARE_APP_NETWORK is required." >&2
  exit 1
fi

awk -v selected_list="${SELECTED_RAW}" '
  BEGIN {
    split(selected_list, arr, ",");
    for (i in arr) { sel[arr[i]] = 1; }
    in_block = 0; emit = 1;
  }
  /^[[:space:]]*# \[[^/].*\]/ {
    tag=$0; sub(/^[[:space:]]*# \[/, "", tag); sub(/\].*$/, "", tag);
    in_block = 1;
    emit = (tag in sel);
    next;
  }
  /^[[:space:]]*# \[\/.*\]/ {
    in_block = 0;
    emit = 1;
    next;
  }
  {
    if (!in_block || emit) { print; }
  }
' "$CONFIG_PATH" > "$GENERATED_CONFIG_PATH"

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

echo
echo "Default cloudflared image: ${CLOUDFLARE_IMAGE}:${CLOUDFLARE_IMAGE_TAG}"
read -r -p "Override cloudflared image tag? [y/N]: " OVERRIDE_TAG
OVERRIDE_TAG="${OVERRIDE_TAG:-N}"
if [[ "$OVERRIDE_TAG" =~ ^[Yy]$ ]]; then
  read -r -p "Enter image tag (e.g. 2024.12.0): " NEW_TAG
  NEW_TAG="${NEW_TAG// /}"
  if [[ -n "$NEW_TAG" ]]; then
    CLOUDFLARE_IMAGE_TAG="$NEW_TAG"
  fi
fi

if [[ -z "$CLOUDFLARE_IMAGE_TAG" || "$CLOUDFLARE_IMAGE_TAG" == "TBD" ]]; then
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update VMs/Cloudflare Tunnel (via Docker)/requirements.txt." >&2
  exit 1
fi

export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH
export CLOUDFLARE_APP_NETWORK

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
