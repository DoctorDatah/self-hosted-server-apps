#!/usr/bin/env bash
set -euo pipefail

# Requires Docker (and deps) and runs Cloudflare Tunnel (cloudflared) via Docker Compose on the VM.
# Expects the repo to be present on the VM.

# --- Help / usage ---

show_usage() {
  cat <<'USAGE'
Usage: ./cloudflare_install_and_setup.sh [--pull] [--down]

Requires:
  - Repo cloned on the VM
  - VMs/install/install_all.sh has been run (Docker + deps installed)
  - VMs/Cloudflare Tunnel - via Docker/config.yml
  - VMs/Cloudflare Tunnel - via Docker/docker-compose.yml
  - VMs/Cloudflare Tunnel - via Docker/requirements.txt

Flags:
  --pull         Pull latest images before starting
  --down         Stop the tunnel instead of starting
USAGE
}

# --- Argument parsing ---
if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  show_usage
  exit 0
fi

pull=false
down=false

while [[ $# -gt 0 ]]; do
  case "$1" in
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

# --- Paths and prerequisites ---
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)
if [[ -z "$REPO_ROOT" ]]; then
  REPO_ROOT="$SCRIPT_DIR"
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

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: $1 is missing. Please execute the installation module first (VMs/install/install_all.sh)." >&2
    exit 1
  }
}
# --- Ensure Docker is available ---
echo "Checking dependencies..."
require_cmd docker
docker compose version >/dev/null 2>&1 || {
  echo "ERROR: docker compose is missing. Please execute the installation module first (VMs/install/install_all.sh)." >&2
  exit 1
}
echo "Dependencies OK."

# --- Tag selection (ingress) ---
echo
echo "Reading available tags from config..."
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
read -r -p "Select tags (comma-separated, e.g. app-main,app-ws) [required]: " SELECTED_RAW
  SELECTED_RAW="${SELECTED_RAW// /}"
  if [[ -z "${SELECTED_RAW}" ]]; then
    echo "Please select at least one tag."
    continue
  fi
  break
done

# --- App network selection (Docker) ---
IFS=',' read -r FIRST_TAG _ <<< "$SELECTED_RAW"
DEFAULT_APP_NETWORK="appnet"

if [[ "$SELECTED_RAW" == *","* ]]; then
  echo "Note: Multiple tags selected. Ensure all services are reachable on the same network."
fi

echo
echo "Selecting app network..."
read -r -p "Docker network for target app [Default: ${DEFAULT_APP_NETWORK}]: " CLOUDFLARE_APP_NETWORK
CLOUDFLARE_APP_NETWORK="${CLOUDFLARE_APP_NETWORK// /}"
if [[ -z "$CLOUDFLARE_APP_NETWORK" ]]; then
  CLOUDFLARE_APP_NETWORK="$DEFAULT_APP_NETWORK"
fi

if [[ -z "$CLOUDFLARE_APP_NETWORK" ]]; then
  echo "ERROR: CLOUDFLARE_APP_NETWORK is required." >&2
  exit 1
fi

if ! docker network inspect "$CLOUDFLARE_APP_NETWORK" >/dev/null 2>&1; then
  echo "ERROR: Docker network '${CLOUDFLARE_APP_NETWORK}' not found." >&2
  echo "Run the installation module (creates appnet) and deploy the app first." >&2
  exit 1
fi


# --- Required env ---
VMS_ENV_FILE="$REPO_ROOT/VMs/.env"
if [[ -f "$VMS_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$VMS_ENV_FILE"
  set +a
fi
if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" || "${CLOUDFLARE_TUNNEL_TOKEN}" == "." ]]; then
  echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required (set it in VMs/.env or export it in-session)." >&2
  exit 1
fi

# --- Generate config based on tags ---
echo "Generating tunnel config for selected tags..."
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

# --- Load pinned defaults ---
echo "Loading pinned defaults (requirements.txt)..."
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

# --- Image override prompt ---
echo
echo "Selecting cloudflared image..."
echo "Default cloudflared image: ${CLOUDFLARE_IMAGE}:${CLOUDFLARE_IMAGE_TAG}"
read -r -p "Override cloudflared image tag? [Default: N]: " OVERRIDE_TAG
OVERRIDE_TAG="${OVERRIDE_TAG:-N}"
if [[ "$OVERRIDE_TAG" =~ ^[Yy]$ ]]; then
  read -r -p "Enter image tag (e.g. 2024.12.0): " NEW_TAG
  NEW_TAG="${NEW_TAG// /}"
  if [[ -n "$NEW_TAG" ]]; then
    CLOUDFLARE_IMAGE_TAG="$NEW_TAG"
  fi
fi

if [[ -z "$CLOUDFLARE_IMAGE_TAG" || "$CLOUDFLARE_IMAGE_TAG" == "TBD" ]]; then
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update VMs/Cloudflare Tunnel - via Docker/requirements.txt." >&2
  exit 1
fi

# --- Export runtime env for compose ---
export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH
export CLOUDFLARE_APP_NETWORK
export CLOUDFLARE_TUNNEL_ID

# --- Persist env for future compose commands ---
echo "Writing .env for docker compose..."
ENV_FILE="$SCRIPT_DIR/.env"
escape_env() {
  local val="$1"
  val="${val//\\/\\\\}"
  val="${val//\"/\\\"}"
  printf '%s' "$val"
}

{
  echo "# Generated by cloudflare_install_and_setup.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'CLOUDFLARE_IMAGE="%s"\n' "$(escape_env "$CLOUDFLARE_IMAGE")"
  printf 'CLOUDFLARE_IMAGE_TAG="%s"\n' "$(escape_env "$CLOUDFLARE_IMAGE_TAG")"
  printf 'CLOUDFLARE_TUNNEL_TOKEN="%s"\n' "$(escape_env "$CLOUDFLARE_TUNNEL_TOKEN")"
  printf 'CLOUDFLARE_TUNNEL_ID="%s"\n' "$(escape_env "${CLOUDFLARE_TUNNEL_ID-}")"
  printf 'CLOUDFLARE_CONFIG_PATH="%s"\n' "$(escape_env "$CLOUDFLARE_CONFIG_PATH")"
  printf 'CLOUDFLARE_APP_NETWORK="%s"\n' "$(escape_env "$CLOUDFLARE_APP_NETWORK")"
} > "$ENV_FILE"

# --- Run docker compose ---
echo "Starting cloudflared with docker compose..."
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
printf 'docker compose -f %q logs -f\n' "$COMPOSE_FILE"
