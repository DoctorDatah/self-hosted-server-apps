#!/usr/bin/env bash
set -euo pipefail

# Requires Docker (and deps) and runs Cloudflare Tunnel (cloudflared) via Docker Compose on the VM.
# Expects the repo to be present on the VM.

# --- Help / usage ---

show_usage() {
  cat <<'USAGE'
Usage: ./install.sh [--pull] [--down] [--setup-cloudflare]

Requires:
  - Repo cloned on the VM
  - VMs/install/install_all.sh has been run (Docker + deps installed)
  - VMs/Cloudflare Tunnel - via Docker/config.yml
  - VMs/Cloudflare Tunnel - via Docker/docker-compose.yml
  - VMs/Cloudflare Tunnel - via Docker/requirements.txt

Flags:
  --pull         Pull latest images before starting
  --down         Stop the tunnel instead of starting
  --setup-cloudflare  Create tunnel + DNS in Cloudflare via API
USAGE
}

# --- Argument parsing ---
if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  show_usage
  exit 0
fi

pull=false
down=false
setup_cloudflare=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)
      pull=true
      ;;
    --down)
      down=true
      ;;
    --setup-cloudflare)
      setup_cloudflare=true
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
  read -r -p "Select tags (comma-separated, e.g. app-main,app-ws): " SELECTED_RAW
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
read -r -p "Docker network for target app [${DEFAULT_APP_NETWORK}]: " CLOUDFLARE_APP_NETWORK
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

# --- Optional Cloudflare API setup ---
if [[ "$setup_cloudflare" == "true" ]]; then
  echo
  echo "Cloudflare API setup enabled; this will create/verify tunnel + DNS."
  require_cmd curl
  require_cmd python3

  echo
  read -r -p "Cloudflare Account ID: " CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID// /}"
  if [[ -z "$CLOUDFLARE_ACCOUNT_ID" ]]; then
    echo "ERROR: Cloudflare Account ID is required." >&2
    exit 1
  fi

  read -r -p "Cloudflare Zone ID: " CLOUDFLARE_ZONE_ID
  CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID// /}"
  if [[ -z "$CLOUDFLARE_ZONE_ID" ]]; then
    echo "ERROR: Cloudflare Zone ID is required." >&2
    exit 1
  fi

  if [[ -z "${CLOUDFLARE_API_TOKEN-}" ]]; then
    read -r -s -p "Cloudflare API Token (Account: Tunnel Edit, Zone: DNS Edit): " CLOUDFLARE_API_TOKEN
    echo
  fi

  if [[ -z "$CLOUDFLARE_API_TOKEN" ]]; then
    echo "ERROR: Cloudflare API token is required." >&2
    exit 1
  fi

  DEFAULT_TUNNEL_NAME="${FIRST_TAG}-tunnel"
  read -r -p "Tunnel name [${DEFAULT_TUNNEL_NAME}]: " CLOUDFLARE_TUNNEL_NAME
  CLOUDFLARE_TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME// /}"
  if [[ -z "$CLOUDFLARE_TUNNEL_NAME" ]]; then
    CLOUDFLARE_TUNNEL_NAME="$DEFAULT_TUNNEL_NAME"
  fi

  echo "Checking for existing tunnel..."
  TUNNEL_LIST_JSON=$(curl -sS \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel")

  EXISTING_TUNNEL_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
name=sys.argv[1];
for t in data.get("result") or []:
  if t.get("name") == name:
    print(t.get("id") or ""); break' "$CLOUDFLARE_TUNNEL_NAME" <<<"$TUNNEL_LIST_JSON")

  if [[ -n "$EXISTING_TUNNEL_ID" ]]; then
    echo "Found existing tunnel with name '${CLOUDFLARE_TUNNEL_NAME}'."
    echo "Choose action:"
    echo "  1) Reuse existing tunnel (token auto-fetch; manual only if API fails)"
    echo "  2) Delete existing tunnel and create a new one"
    echo "  3) Choose a different tunnel name"
    read -r -p "Select [1/2/3]: " TUNNEL_ACTION
    case "$TUNNEL_ACTION" in
      1)
        CLOUDFLARE_TUNNEL_ID="$EXISTING_TUNNEL_ID"
        if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" ]]; then
          echo "Fetching existing tunnel token..."
          TOKEN_JSON=$(curl -sS \
            -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
            -H "Content-Type: application/json" \
            "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${CLOUDFLARE_TUNNEL_ID}/token")
          CLOUDFLARE_TUNNEL_TOKEN=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("", end=""); sys.exit(0)
print(data.get("result") or "")' <<<"$TOKEN_JSON")
        fi
        if [[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]]; then
          read -r -s -p "Existing tunnel token (manual): " CLOUDFLARE_TUNNEL_TOKEN
          echo
        fi
        if [[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]]; then
          echo "ERROR: Tunnel token is required to reuse an existing tunnel." >&2
          exit 1
        fi
        ;;
      2)
        echo "Deleting existing tunnel ${EXISTING_TUNNEL_ID}..."
        DELETE_JSON=$(curl -sS \
          -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
          -H "Content-Type: application/json" \
          -X DELETE \
          "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${EXISTING_TUNNEL_ID}")
        python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("ERROR: Tunnel delete failed:", data.get("errors") or data, file=sys.stderr); sys.exit(1)
' <<<"$DELETE_JSON" || exit 1
        ;;
      3)
        read -r -p "New tunnel name: " CLOUDFLARE_TUNNEL_NAME
        CLOUDFLARE_TUNNEL_NAME="${CLOUDFLARE_TUNNEL_NAME// /}"
        if [[ -z "$CLOUDFLARE_TUNNEL_NAME" ]]; then
          echo "ERROR: Tunnel name is required." >&2
          exit 1
        fi
        ;;
      *)
        echo "ERROR: Invalid selection." >&2
        exit 1
        ;;
    esac
  fi

  if [[ -z "${CLOUDFLARE_TUNNEL_ID-}" ]]; then
    echo "Creating Cloudflare Tunnel..."
    TUNNEL_CREATE_JSON=$(curl -sS \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -X POST \
      "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel" \
      --data "{\"name\":\"${CLOUDFLARE_TUNNEL_NAME}\",\"config_src\":\"local\"}")

    python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("ERROR: Tunnel create failed:", data.get("errors") or data, file=sys.stderr); sys.exit(1)
result=data.get("result") or {}
if not result.get("token") or not result.get("id"):
  print("ERROR: Tunnel create response missing token/id.", file=sys.stderr); sys.exit(1)
' <<<"$TUNNEL_CREATE_JSON" || exit 1

    CLOUDFLARE_TUNNEL_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["result"]["id"])' <<<"$TUNNEL_CREATE_JSON")
    CLOUDFLARE_TUNNEL_TOKEN=$(python3 -c 'import json,sys; data=json.load(sys.stdin); print(data["result"]["token"])' <<<"$TUNNEL_CREATE_JSON")
  fi

  echo
  read -r -p "Public hostname (e.g. coolify.arshware.com): " CLOUDFLARE_DNS_HOSTNAME
  CLOUDFLARE_DNS_HOSTNAME="${CLOUDFLARE_DNS_HOSTNAME// /}"
  if [[ -n "$CLOUDFLARE_DNS_HOSTNAME" ]]; then
    echo "Creating DNS CNAME -> ${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com ..."
    DNS_CREATE_JSON=$(curl -sS \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -X POST \
      "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
      --data "{\"type\":\"CNAME\",\"name\":\"${CLOUDFLARE_DNS_HOSTNAME}\",\"content\":\"${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com\",\"proxied\":true}")
    if ! python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  sys.exit(1)
' <<<"$DNS_CREATE_JSON"; then
      echo "DNS create failed; attempting to update existing record..."
      DNS_LOOKUP_JSON=$(curl -sS \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=CNAME&name=${CLOUDFLARE_DNS_HOSTNAME}")
      DNS_RECORD_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
records=data.get("result") or []
print(records[0]["id"] if records else "")' <<<"$DNS_LOOKUP_JSON")
      if [[ -n "$DNS_RECORD_ID" ]]; then
        DNS_UPDATE_JSON=$(curl -sS \
          -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
          -H "Content-Type: application/json" \
          -X PUT \
          "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${DNS_RECORD_ID}" \
          --data "{\"type\":\"CNAME\",\"name\":\"${CLOUDFLARE_DNS_HOSTNAME}\",\"content\":\"${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com\",\"proxied\":true}")
        python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("WARN: DNS record update failed:", data.get("errors") or data, file=sys.stderr); sys.exit(0)
print("DNS record updated.")
' <<<"$DNS_UPDATE_JSON"
      else
        echo "WARN: DNS record not found; please add it manually." >&2
      fi
    else
      echo "DNS record created."
    fi
  else
    echo "Skipping DNS record creation (no hostname provided)."
  fi
fi

# --- Required env ---
if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" || "${CLOUDFLARE_TUNNEL_TOKEN}" == "." ]]; then
  echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required (export it in-session or use --setup-cloudflare)." >&2
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
  echo "# Generated by install.sh on $(date -u +%Y-%m-%dT%H:%M:%SZ)"
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
