#!/usr/bin/env bash
set -euo pipefail

# Cloudflare Tunnel — SSH-only setup via Docker Compose.
# Only prompts for Account ID, API Token, and SSH domain.
# Zone ID, tunnel name, and image tag are derived automatically.

show_usage() {
  cat <<'USAGE'
Usage: ./cloudflare_install_and_setup.sh [--pull] [--down]

Flags:
  --pull    Pull latest images before starting
  --down    Stop the tunnel
USAGE
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then show_usage; exit 0; fi

pull=false
down=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull) pull=true ;;
    --down) down=true ;;
    -h|--help) show_usage; exit 0 ;;
    *) echo "Unknown option: $1" >&2; show_usage; exit 1 ;;
  esac
  shift
done

# ── paths ─────────────────────────────────────────────────────────────────────

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONFIG_PATH="$SCRIPT_DIR/config.yml"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.yml"
DEPS_FILE="$SCRIPT_DIR/requirements.txt"

[[ -f "$CONFIG_PATH" ]]  || { echo "ERROR: Missing $CONFIG_PATH" >&2; exit 1; }
[[ -f "$COMPOSE_FILE" ]] || { echo "ERROR: Missing $COMPOSE_FILE" >&2; exit 1; }
[[ -f "$DEPS_FILE" ]]    || { echo "ERROR: Missing $DEPS_FILE" >&2; exit 1; }

echo "Checking dependencies..."

# ── curl + python3 ────────────────────────────────────────────────────────────
if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
  echo "Installing curl and python3..."
  sudo apt-get update -y -qq
  sudo apt-get install -y -qq curl python3
fi

# ── docker ────────────────────────────────────────────────────────────────────
if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Installing via official script..."
  curl -fsSL https://get.docker.com | sudo sh
  sudo systemctl enable docker
  sudo systemctl start docker
  # allow current user to run docker without sudo
  sudo usermod -aG docker "$USER"
  echo "Docker installed. You may need to log out and back in for group membership to take effect."
fi

# ── docker daemon ─────────────────────────────────────────────────────────────
if ! docker info >/dev/null 2>&1; then
  echo "Docker daemon not running. Starting..."
  sudo systemctl start docker
  docker info >/dev/null 2>&1 || { echo "ERROR: Could not start Docker daemon." >&2; exit 1; }
fi

# ── docker compose plugin ─────────────────────────────────────────────────────
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose plugin not found. Installing..."
  sudo apt-get update -y -qq
  sudo apt-get install -y -qq docker-compose-plugin
  docker compose version >/dev/null 2>&1 || { echo "ERROR: docker compose install failed." >&2; exit 1; }
fi

echo "Dependencies OK."

# ── prompts (only what cannot be derived) ────────────────────────────────────

echo
read -r -p "Cloudflare Account ID: " CLOUDFLARE_ACCOUNT_ID
CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID// /}"
[[ -n "$CLOUDFLARE_ACCOUNT_ID" ]] || { echo "ERROR: Account ID is required." >&2; exit 1; }

read -r -s -p "Cloudflare API Token (Tunnel Edit + DNS Edit): " CLOUDFLARE_API_TOKEN
echo
[[ -n "$CLOUDFLARE_API_TOKEN" ]] || { echo "ERROR: API Token is required." >&2; exit 1; }

read -r -p "SSH domain (e.g. ssh.hermes-dev.arshware.com): " SSH_DOMAIN
SSH_DOMAIN="${SSH_DOMAIN// /}"
[[ -n "$SSH_DOMAIN" ]] || { echo "ERROR: SSH domain is required." >&2; exit 1; }

# ── derive zone id from domain ────────────────────────────────────────────────

ZONE_NAME=$(echo "$SSH_DOMAIN" | awk -F. '{print $(NF-1)"."$NF}')
echo
echo "Looking up Zone ID for ${ZONE_NAME}..."
ZONE_JSON=$(curl -sS \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/zones?name=${ZONE_NAME}&account.id=${CLOUDFLARE_ACCOUNT_ID}")

CLOUDFLARE_ZONE_ID=$(python3 -c '
import json,sys
data=json.load(sys.stdin)
results=data.get("result") or []
print(results[0]["id"] if results else "")
' <<<"$ZONE_JSON")

[[ -n "$CLOUDFLARE_ZONE_ID" ]] || { echo "ERROR: Could not find Zone ID for ${ZONE_NAME}. Check Account ID and token permissions." >&2; exit 1; }
echo "Zone ID: ${CLOUDFLARE_ZONE_ID}"

# ── derive tunnel name from domain ────────────────────────────────────────────

CLOUDFLARE_TUNNEL_NAME=$(echo "$SSH_DOMAIN" | sed 's/\./-/g')-tunnel
echo "Tunnel name: ${CLOUDFLARE_TUNNEL_NAME}"

# ── check for existing tunnel ─────────────────────────────────────────────────

echo
echo "Checking for existing tunnel..."
TUNNEL_LIST_JSON=$(curl -sS \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel")

EXISTING_TUNNEL_ID=$(python3 -c '
import json,sys
data=json.load(sys.stdin)
name=sys.argv[1]
for t in data.get("result") or []:
  if t.get("name")==name:
    print(t.get("id") or ""); break
' "$CLOUDFLARE_TUNNEL_NAME" <<<"$TUNNEL_LIST_JSON")

CLOUDFLARE_TUNNEL_ID=""
CLOUDFLARE_TUNNEL_TOKEN=""

if [[ -n "$EXISTING_TUNNEL_ID" ]]; then
  echo "Found existing tunnel '${CLOUDFLARE_TUNNEL_NAME}'."
  echo "  1) Reuse"
  echo "  2) Delete and recreate"
  read -r -p "Select [1/2]: " TUNNEL_ACTION

  case "$TUNNEL_ACTION" in
    1)
      CLOUDFLARE_TUNNEL_ID="$EXISTING_TUNNEL_ID"
      echo "Fetching tunnel token..."
      TOKEN_JSON=$(curl -sS \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${CLOUDFLARE_TUNNEL_ID}/token")
      CLOUDFLARE_TUNNEL_TOKEN=$(python3 -c '
import json,sys
data=json.load(sys.stdin)
print(data.get("result") or "")' <<<"$TOKEN_JSON")
      if [[ -z "$CLOUDFLARE_TUNNEL_TOKEN" ]]; then
        read -r -s -p "Could not fetch token. Enter manually: " CLOUDFLARE_TUNNEL_TOKEN
        echo
      fi
      ;;
    2)
      echo "Deleting tunnel ${EXISTING_TUNNEL_ID}..."
      curl -sS -X DELETE \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel/${EXISTING_TUNNEL_ID}" >/dev/null
      ;;
    *)
      echo "ERROR: Invalid selection." >&2; exit 1 ;;
  esac
fi

# ── create tunnel if needed ───────────────────────────────────────────────────

if [[ -z "$CLOUDFLARE_TUNNEL_ID" ]]; then
  echo "Creating tunnel '${CLOUDFLARE_TUNNEL_NAME}'..."
  TUNNEL_CREATE_JSON=$(curl -sS \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    -X POST \
    "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/cfd_tunnel" \
    --data "{\"name\":\"${CLOUDFLARE_TUNNEL_NAME}\",\"config_src\":\"local\"}")

  python3 -c '
import json,sys
data=json.load(sys.stdin)
if not data.get("success"):
  print("ERROR: Tunnel create failed:", data.get("errors"), file=sys.stderr); sys.exit(1)
' <<<"$TUNNEL_CREATE_JSON" || exit 1

  CLOUDFLARE_TUNNEL_ID=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["result"]["id"])' <<<"$TUNNEL_CREATE_JSON")
  CLOUDFLARE_TUNNEL_TOKEN=$(python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["result"]["token"])' <<<"$TUNNEL_CREATE_JSON")
fi

[[ -n "$CLOUDFLARE_TUNNEL_TOKEN" ]] || { echo "ERROR: Tunnel token is empty." >&2; exit 1; }

# ── dns record ────────────────────────────────────────────────────────────────

echo "Creating DNS CNAME ${SSH_DOMAIN} → ${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com ..."
DNS_JSON=$(curl -sS \
  -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -X POST \
  "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records" \
  --data "{\"type\":\"CNAME\",\"name\":\"${SSH_DOMAIN}\",\"content\":\"${CLOUDFLARE_TUNNEL_ID}.cfargotunnel.com\",\"proxied\":true}")

if python3 -c 'import json,sys; d=json.load(sys.stdin); sys.exit(0 if d.get("success") else 1)' <<<"$DNS_JSON" 2>/dev/null; then
  echo "DNS record created."
else
  echo "WARN: DNS create failed or record already exists. Verify in Cloudflare dashboard." >&2
fi

# ── generate config for this vm ──────────────────────────────────────────────

GENERATED_CONFIG="$SCRIPT_DIR/config.generated.yml"
sed "s/__SSH_DOMAIN__/${SSH_DOMAIN}/g" "$CONFIG_PATH" > "$GENERATED_CONFIG"
echo "Generated config: ${GENERATED_CONFIG}"

# ── load image from requirements.txt ─────────────────────────────────────────

while IFS='=' read -r key val; do
  [[ -z "${key// }" || "${key:0:1}" == "#" ]] && continue
  key="$(echo "$key" | xargs)"
  val="$(echo "${val-}" | xargs)"
  [[ -n "$key" ]] && export "$key=$val"
done < "$DEPS_FILE"

CLOUDFLARE_IMAGE="${CLOUDFLARE_IMAGE:-cloudflare/cloudflared}"
[[ -n "${CLOUDFLARE_IMAGE_TAG:-}" && "${CLOUDFLARE_IMAGE_TAG}" != "TBD" ]] || {
  echo "ERROR: CLOUDFLARE_IMAGE_TAG not set. Update requirements.txt." >&2; exit 1
}

echo "Using image: ${CLOUDFLARE_IMAGE}:${CLOUDFLARE_IMAGE_TAG}"

# ── export for docker compose (in-session only) ───────────────────────────────

export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH="$GENERATED_CONFIG"
export CLOUDFLARE_TUNNEL_TOKEN
export CLOUDFLARE_TUNNEL_ID

# ── run ───────────────────────────────────────────────────────────────────────

cd "$SCRIPT_DIR"

if [[ "$down" == "true" ]]; then
  docker compose -f "$COMPOSE_FILE" down
  exit 0
fi

[[ "$pull" == "true" ]] && docker compose -f "$COMPOSE_FILE" pull

docker compose -f "$COMPOSE_FILE" up -d

echo
echo "cloudflared started. Check logs with:"
printf 'docker compose -f %q logs -f\n' "$COMPOSE_FILE"
