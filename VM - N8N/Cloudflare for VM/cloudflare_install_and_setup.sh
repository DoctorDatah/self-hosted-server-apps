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
  - VM - N8N/Installations/install_all.sh has been run (Docker + deps installed)
  - VM - N8N/Cloudflare for VM/config.yml
  - VM - N8N/Cloudflare for VM/docker-compose.yml
  - VM - N8N/Cloudflare for VM/requirements.txt

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
    echo "ERROR: $1 is missing. Please execute the installation module first (VM - N8N/Installations/install_all.sh)." >&2
    exit 1
  }
}
# --- Ensure Docker is available ---
echo "Checking dependencies..."
require_cmd docker
docker compose version >/dev/null 2>&1 || {
  echo "ERROR: docker compose is missing. Please execute the installation module first (VM - N8N/Installations/install_all.sh)." >&2
  exit 1
}
echo "Dependencies OK."

# --- Config (SSH-only) ---
echo
echo "Using SSH-only config at: $CONFIG_PATH"


# --- Cloudflare API setup (always) ---
echo
echo "Cloudflare API setup enabled; this will create/verify tunnel + DNS."
require_cmd curl
require_cmd python3

INFISICAL_ENV_FILE="$SCRIPT_DIR/.infisical.cloudflare.env"
if [[ -f "$INFISICAL_ENV_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$INFISICAL_ENV_FILE"
  set +a
fi

if [[ -z "${CLOUDFLARE_ACCOUNT_ID-}" && -n "${Cloudflare_Account_ID-}" ]]; then
  CLOUDFLARE_ACCOUNT_ID="$Cloudflare_Account_ID"
fi
if [[ -z "${CLOUDFLARE_ZONE_ID-}" && -n "${Cloudflare_Zone_ID-}" ]]; then
  CLOUDFLARE_ZONE_ID="$Cloudflare_Zone_ID"
fi
if [[ -z "${CLOUDFLARE_API_TOKEN-}" && -n "${Cloudflare_Token-}" ]]; then
  CLOUDFLARE_API_TOKEN="$Cloudflare_Token"
fi

# Load from local .env if present (safe parser; supports spaces)
LOCAL_ENV_FILE="$SCRIPT_DIR/.env"
load_env_file() {
  local file="$1"
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "${line// }" || "${line:0:1}" == "#" ]] && continue
    key="${line%%=*}"
    val="${line#*=}"
    # Strip optional surrounding quotes
    if [[ "${val:0:1}" == "\"" && "${val: -1}" == "\"" ]]; then
      val="${val:1:${#val}-2}"
    fi
    if [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      export "$key=$val"
    else
      echo "WARN: Skipping invalid env key '$key' from $file" >&2
    fi
  done < "$file"
}
if [[ -f "$LOCAL_ENV_FILE" ]]; then
  load_env_file "$LOCAL_ENV_FILE"
fi

# Normalize tunnel ID if it came with embedded quotes.
if [[ -n "${CLOUDFLARE_TUNNEL_ID-}" ]]; then
  CLOUDFLARE_TUNNEL_ID="${CLOUDFLARE_TUNNEL_ID//\"/}"
  CLOUDFLARE_TUNNEL_ID="${CLOUDFLARE_TUNNEL_ID//\'/}"
  CLOUDFLARE_TUNNEL_ID="${CLOUDFLARE_TUNNEL_ID//\\/}"
fi

require_env_var() {
  local key="$1"
  if [[ -z "${!key-}" ]]; then
    echo "ERROR: ${key} is required. Run cloudflare_env_setup.sh first." >&2
    exit 1
  fi
}

require_env_var "CLOUDFLARE_IMAGE"
require_env_var "CLOUDFLARE_IMAGE_TAG"
require_env_var "CLOUDFLARE_CONFIG_PATH"
if [[ -z "${CLOUDFLARE_ACCOUNT_ID-}" && -n "${Cloudflare_Account_ID-}" ]]; then
  CLOUDFLARE_ACCOUNT_ID="$Cloudflare_Account_ID"
fi
if [[ -z "${CLOUDFLARE_ZONE_ID-}" && -n "${Cloudflare_Zone_ID-}" ]]; then
  CLOUDFLARE_ZONE_ID="$Cloudflare_Zone_ID"
fi
if [[ -z "${CLOUDFLARE_API_TOKEN-}" && -n "${Cloudflare_Token-}" ]]; then
  CLOUDFLARE_API_TOKEN="$Cloudflare_Token"
fi

echo
if [[ -z "${CLOUDFLARE_ACCOUNT_ID-}" ]]; then
  read -r -p "Cloudflare Account ID [required]: " CLOUDFLARE_ACCOUNT_ID
  CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID// /}"
fi
if [[ -z "${CLOUDFLARE_ACCOUNT_ID-}" ]]; then
  echo "ERROR: Cloudflare Account ID is required." >&2
  exit 1
fi

if [[ -z "${CLOUDFLARE_ZONE_ID-}" ]]; then
  read -r -p "Cloudflare Zone ID [required]: " CLOUDFLARE_ZONE_ID
  CLOUDFLARE_ZONE_ID="${CLOUDFLARE_ZONE_ID// /}"
fi
if [[ -z "${CLOUDFLARE_ZONE_ID-}" ]]; then
  echo "ERROR: Cloudflare Zone ID is required." >&2
  exit 1
fi

if [[ -z "${CLOUDFLARE_API_TOKEN-}" ]]; then
  read -r -s -p "Cloudflare API Token (Account: Tunnel Edit, Zone: DNS Edit) [required]: " CLOUDFLARE_API_TOKEN
  echo
fi
if [[ -z "${CLOUDFLARE_API_TOKEN-}" ]]; then
  echo "ERROR: Cloudflare API token is required." >&2
  exit 1
fi

DEFAULT_TUNNEL_NAME="vm-ssh-tunnel"
read -r -p "Tunnel name [Default: ${DEFAULT_TUNNEL_NAME}]: " CLOUDFLARE_TUNNEL_NAME
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
      if ! python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("ERROR: Tunnel delete failed:", data.get("errors") or data, file=sys.stderr); sys.exit(1)
' <<<"$DELETE_JSON"; then
        if python3 -c 'import json,sys; data=json.load(sys.stdin);
errs=data.get("errors") or []
msg=" ".join(e.get("message","") for e in errs)
sys.exit(0 if "active connections" in msg.lower() else 1)
' <<<"$DELETE_JSON"; then
          echo "Tunnel has active connections."
          echo "Choose action:"
          echo "  1) Stop cloudflared container and retry delete"
          echo "  2) Reuse existing tunnel (no delete)"
          echo "  3) Abort"
          read -r -p "Select [1/2/3]: " ACTIVE_ACTION
          case "$ACTIVE_ACTION" in
            1)
              echo "Stopping cloudflared..."
              docker compose -f "$COMPOSE_FILE" down || true
              echo "Retrying delete..."
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
            2)
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
            *)
              echo "Aborting."
              exit 1
              ;;
          esac
        else
          exit 1
        fi
      fi
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

# --- Persist token locally (.env) ---
LOCAL_ENV_FILE="$SCRIPT_DIR/.env"
escape_env() {
  local val="$1"
  val="${val//\\/\\\\}"
  val="${val//\"/\\\"}"
  printf '%s' "$val"
}
upsert_env_var() {
  local key="$1"
  local val="$2"
  local file="$3"
  if [[ -f "$file" ]] && grep -qE "^${key}=" "$file"; then
    awk -v k="$key" -v v="$val" '
      BEGIN { updated=0 }
      $0 ~ "^"k"=" { print k"=\""v"\""; updated=1; next }
      { print }
      END { if (!updated) print k"=\""v"\"" }
    ' "$file" > "${file}.tmp" && mv "${file}.tmp" "$file"
  else
    printf '%s="%s"\n' "$key" "$val" >> "$file"
  fi
}

if [[ -n "${CLOUDFLARE_TUNNEL_TOKEN-}" ]]; then
  echo "Saving tunnel token to local .env..."
  upsert_env_var "CLOUDFLARE_TUNNEL_TOKEN" "$(escape_env "$CLOUDFLARE_TUNNEL_TOKEN")" "$LOCAL_ENV_FILE"
fi
if [[ -n "${CLOUDFLARE_TUNNEL_ID-}" ]]; then
  upsert_env_var "CLOUDFLARE_TUNNEL_ID" "$(escape_env "$CLOUDFLARE_TUNNEL_ID")" "$LOCAL_ENV_FILE"
fi

echo
read -r -p "Public hostname (e.g. coolify.arshware.com) — must match the DNS record you want Cloudflare to update (CNAME to the tunnel): " CLOUDFLARE_DNS_HOSTNAME
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

  # Ensure record is proxied (orange cloud).
  DNS_CHECK_JSON=$(curl -sS \
    -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
    -H "Content-Type: application/json" \
    "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records?type=CNAME&name=${CLOUDFLARE_DNS_HOSTNAME}")
  DNS_RECORD_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
records=data.get("result") or []
print(records[0]["id"] if records else "")' <<<"$DNS_CHECK_JSON")
  DNS_PROXIED=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
records=data.get("result") or []
print("true" if (records and records[0].get("proxied")) else "false")' <<<"$DNS_CHECK_JSON")
  if [[ -n "$DNS_RECORD_ID" && "$DNS_PROXIED" != "true" ]]; then
    echo "DNS record is not proxied; enabling proxy (orange cloud)..."
    DNS_PROXY_JSON=$(curl -sS \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      -X PATCH \
      "https://api.cloudflare.com/client/v4/zones/${CLOUDFLARE_ZONE_ID}/dns_records/${DNS_RECORD_ID}" \
      --data "{\"proxied\":true}")
    python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("WARN: Failed to enable proxy:", data.get("errors") or data, file=sys.stderr); sys.exit(0)
print("DNS proxy enabled.")' <<<"$DNS_PROXY_JSON"
  fi
else
  echo "Skipping DNS record creation (no hostname provided)."
fi

# --- Cloudflare Access app + policy (SSH) ---
if [[ -n "$CLOUDFLARE_DNS_HOSTNAME" ]]; then
  echo
  read -r -p "Create/Update Cloudflare Access SSH app + allow policy for ${CLOUDFLARE_DNS_HOSTNAME}? [Default: Y]: " ACCESS_CREATE
  ACCESS_CREATE="${ACCESS_CREATE:-Y}"
  if [[ "$ACCESS_CREATE" =~ ^[Yy]$ ]]; then
    DEFAULT_ACCESS_APP_NAME="SSH - ${CLOUDFLARE_DNS_HOSTNAME}"
    read -r -p "Access app name [Default: ${DEFAULT_ACCESS_APP_NAME}]: " ACCESS_APP_NAME
    ACCESS_APP_NAME="${ACCESS_APP_NAME// /}"
    if [[ -z "$ACCESS_APP_NAME" ]]; then
      ACCESS_APP_NAME="$DEFAULT_ACCESS_APP_NAME"
    fi

    DEFAULT_SESSION_DURATION="24h"
    read -r -p "Access session duration [Default: ${DEFAULT_SESSION_DURATION}]: " ACCESS_SESSION_DURATION
    ACCESS_SESSION_DURATION="${ACCESS_SESSION_DURATION// /}"
    if [[ -z "$ACCESS_SESSION_DURATION" ]]; then
      ACCESS_SESSION_DURATION="$DEFAULT_SESSION_DURATION"
    fi

    read -r -p "Allow email(s) for Access policy (comma-separated) [required]: " ACCESS_EMAILS
    ACCESS_EMAILS="${ACCESS_EMAILS// /}"
    export ACCESS_APP_NAME ACCESS_SESSION_DURATION ACCESS_EMAILS CLOUDFLARE_DNS_HOSTNAME

    echo "Checking for existing Access app..."
    ACCESS_LIST_JSON=$(curl -sS \
      -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
      -H "Content-Type: application/json" \
      "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps?domain=${CLOUDFLARE_DNS_HOSTNAME}")

    ACCESS_APP_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
app_id=""
for app in data.get("result") or []:
  if app.get("domain") == sys.argv[1]:
    app_id = app.get("id") or ""
    break
print(app_id)' "$CLOUDFLARE_DNS_HOSTNAME" <<<"$ACCESS_LIST_JSON")

    if [[ -n "$ACCESS_APP_ID" ]]; then
      echo "Access app already exists for ${CLOUDFLARE_DNS_HOSTNAME}."
      read -r -p "Replace existing Access app (delete + recreate)? [Default: N]: " REPLACE_ACCESS_APP
      REPLACE_ACCESS_APP="${REPLACE_ACCESS_APP:-N}"
      if [[ "$REPLACE_ACCESS_APP" =~ ^[Yy]$ ]]; then
        echo "Deleting existing Access app..."
        ACCESS_DELETE_JSON=$(curl -sS \
          -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
          -H "Content-Type: application/json" \
          -X DELETE \
          "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${ACCESS_APP_ID}")
        if ! python3 -c 'import json,sys; data=json.load(sys.stdin);
sys.exit(0 if data.get("success") else 1)' <<<"$ACCESS_DELETE_JSON"; then
          echo "WARN: Failed to delete Access app. Aborting Access setup." >&2
          ACCESS_APP_ID=""
        else
          ACCESS_APP_ID=""
        fi
      fi
    fi

    if [[ -z "$ACCESS_APP_ID" ]]; then
      echo "Creating Access app..."
      ACCESS_CREATE_BODY=$(python3 - <<'PY'
import json, os
body = {
  "name": os.environ.get("ACCESS_APP_NAME", "SSH Access"),
  "domain": os.environ.get("CLOUDFLARE_DNS_HOSTNAME"),
  "type": "ssh",
  "session_duration": os.environ.get("ACCESS_SESSION_DURATION", "24h"),
}
print(json.dumps(body))
PY
)
      ACCESS_CREATE_JSON=$(curl -sS \
        -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
        -H "Content-Type: application/json" \
        -X POST \
        "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps" \
        --data "${ACCESS_CREATE_BODY}")
      ACCESS_APP_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
if not data.get("success"):
  print("", end=""); sys.exit(0)
print((data.get("result") or {}).get("id") or "")' <<<"$ACCESS_CREATE_JSON")
      if [[ -z "$ACCESS_APP_ID" ]]; then
        echo "WARN: Access app creation failed. Check API token permissions (Access: Apps and Policies)." >&2
      fi
    fi

    if [[ -n "$ACCESS_APP_ID" ]]; then
      if [[ -z "$ACCESS_EMAILS" ]]; then
        echo "WARN: No emails provided; skipping Access policy creation." >&2
      else
        DEFAULT_POLICY_NAME="Allow SSH"
        read -r -p "Access policy name [Default: ${DEFAULT_POLICY_NAME}]: " ACCESS_POLICY_NAME
        ACCESS_POLICY_NAME="${ACCESS_POLICY_NAME// /}"
        if [[ -z "$ACCESS_POLICY_NAME" ]]; then
          ACCESS_POLICY_NAME="$DEFAULT_POLICY_NAME"
        fi
        export ACCESS_POLICY_NAME

        echo "Checking for existing Access policy..."
        POLICY_LIST_JSON=$(curl -sS \
          -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
          -H "Content-Type: application/json" \
          "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${ACCESS_APP_ID}/policies")

        EXISTING_POLICY_ID=$(python3 -c 'import json,sys; data=json.load(sys.stdin);
name=sys.argv[1];
policy_id=""
for p in data.get("result") or []:
  if p.get("name") == name:
    policy_id = p.get("id") or ""
    break
print(policy_id)' "$ACCESS_POLICY_NAME" <<<"$POLICY_LIST_JSON")

        if [[ -n "$EXISTING_POLICY_ID" ]]; then
          echo "Access policy '${ACCESS_POLICY_NAME}' already exists."
          read -r -p "Replace existing Access policy (delete + recreate)? [Default: N]: " REPLACE_ACCESS_POLICY
          REPLACE_ACCESS_POLICY="${REPLACE_ACCESS_POLICY:-N}"
          if [[ "$REPLACE_ACCESS_POLICY" =~ ^[Yy]$ ]]; then
            echo "Deleting existing Access policy..."
            POLICY_DELETE_JSON=$(curl -sS \
              -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
              -H "Content-Type: application/json" \
              -X DELETE \
              "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${ACCESS_APP_ID}/policies/${EXISTING_POLICY_ID}")
            if ! python3 -c 'import json,sys; data=json.load(sys.stdin);
sys.exit(0 if data.get("success") else 1)' <<<"$POLICY_DELETE_JSON"; then
              echo "WARN: Failed to delete Access policy. Skipping policy creation." >&2
              EXISTING_POLICY_ID=""
            else
              EXISTING_POLICY_ID=""
            fi
          fi
        fi
        if [[ -z "$EXISTING_POLICY_ID" ]]; then
          echo "Creating Access policy..."
          ACCESS_POLICY_BODY=$(python3 - <<'PY'
import json, os
emails = [e for e in os.environ.get("ACCESS_EMAILS","").split(",") if e]
include = [{"email": {"email": e}} for e in emails]
body = {
  "name": os.environ.get("ACCESS_POLICY_NAME", "Allow SSH"),
  "decision": "allow",
  "include": include,
  "exclude": [],
  "require": []
}
print(json.dumps(body))
PY
)
          POLICY_CREATE_JSON=$(curl -sS \
            -H "Authorization: Bearer ${CLOUDFLARE_API_TOKEN}" \
            -H "Content-Type: application/json" \
            -X POST \
            "https://api.cloudflare.com/client/v4/accounts/${CLOUDFLARE_ACCOUNT_ID}/access/apps/${ACCESS_APP_ID}/policies" \
            --data "${ACCESS_POLICY_BODY}")
          if ! python3 -c 'import json,sys; data=json.load(sys.stdin);
sys.exit(0 if data.get("success") else 1)' <<<"$POLICY_CREATE_JSON"; then
            echo "WARN: Access policy creation failed. Check inputs and API token permissions." >&2
          else
            echo "Access policy created."
          fi
        fi
      fi
    fi
  fi
fi

# --- Wait for TLS to become active (optional) ---
if [[ -n "$CLOUDFLARE_DNS_HOSTNAME" ]]; then
  echo
  read -r -p "Wait for TLS to become active for https://${CLOUDFLARE_DNS_HOSTNAME}? [Default: Y]: " WAIT_TLS
  WAIT_TLS="${WAIT_TLS:-Y}"
  if [[ "$WAIT_TLS" =~ ^[Yy]$ ]]; then
    MAX_WAIT_SECONDS=180
    SLEEP_SECONDS=5
    ELAPSED=0
    echo "Waiting for TLS (up to ${MAX_WAIT_SECONDS}s)..."
    while true; do
      if curl -sS --max-time 5 -I "https://${CLOUDFLARE_DNS_HOSTNAME}" >/dev/null 2>&1; then
        echo "TLS is active for https://${CLOUDFLARE_DNS_HOSTNAME}"
        break
      fi
      sleep "$SLEEP_SECONDS"
      ELAPSED=$((ELAPSED + SLEEP_SECONDS))
      if [[ "$ELAPSED" -ge "$MAX_WAIT_SECONDS" ]]; then
        echo "WARN: TLS not active yet. Try again in a few minutes." >&2
        break
      fi
    done
  fi
fi

if [[ -z "${CLOUDFLARE_TUNNEL_TOKEN-}" || "${CLOUDFLARE_TUNNEL_TOKEN}" == "." ]]; then
  echo "ERROR: CLOUDFLARE_TUNNEL_TOKEN is required (set it in local .env or export it in-session)." >&2
  exit 1
fi

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

CLOUDFLARE_CONFIG_PATH=${CLOUDFLARE_CONFIG_PATH:-$CONFIG_PATH}

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
  echo "ERROR: CLOUDFLARE_IMAGE_TAG is not set. Update VM - N8N/Cloudflare for VM/requirements.txt." >&2
  exit 1
fi

# --- Export runtime env for compose ---
export CLOUDFLARE_IMAGE
export CLOUDFLARE_IMAGE_TAG
export CLOUDFLARE_CONFIG_PATH
export CLOUDFLARE_TUNNEL_ID

# --- Run docker compose ---
echo "Starting cloudflared with docker compose..."
cd "$REPO_ROOT"

if [[ "$down" == "true" ]]; then
  if [[ ! -f "$LOCAL_ENV_FILE" ]]; then
    echo "ERROR: Missing local .env at $LOCAL_ENV_FILE. Run cloudflare_env_setup.sh first." >&2
    exit 1
  fi
  docker compose --env-file "$LOCAL_ENV_FILE" -f "$COMPOSE_FILE" down
  exit 0
fi

if [[ "$pull" == "true" ]]; then
  if [[ ! -f "$LOCAL_ENV_FILE" ]]; then
    echo "ERROR: Missing local .env at $LOCAL_ENV_FILE. Run cloudflare_env_setup.sh first." >&2
    exit 1
  fi
  docker compose --env-file "$LOCAL_ENV_FILE" -f "$COMPOSE_FILE" pull
fi

if [[ ! -f "$LOCAL_ENV_FILE" ]]; then
  echo "ERROR: Missing local .env at $LOCAL_ENV_FILE. Run cloudflare_env_setup.sh first." >&2
  exit 1
fi
docker compose --env-file "$LOCAL_ENV_FILE" -f "$COMPOSE_FILE" up -d

echo "cloudflared is starting. Check logs with:"
printf 'docker compose --env-file %q -f %q logs -f\n' "$LOCAL_ENV_FILE" "$COMPOSE_FILE"
