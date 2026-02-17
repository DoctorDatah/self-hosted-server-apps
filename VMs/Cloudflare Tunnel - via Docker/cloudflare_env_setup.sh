#!/usr/bin/env bash
set -euo pipefail

# Fetches secrets from Infisical and writes Cloudflare Tunnel .env.
# Ubuntu-only script.

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  fi
}

require_ubuntu() {
  if [[ "$(uname -s)" != "Linux" ]]; then
    echo "ERROR: This script supports Ubuntu only." >&2
    exit 1
  fi
  if [[ -f /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    if [[ "${ID:-}" != "ubuntu" ]]; then
      echo "ERROR: This script supports Ubuntu only." >&2
      exit 1
    fi
  else
    echo "ERROR: Unable to verify OS. Ubuntu required." >&2
    exit 1
  fi
}

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OUTPUT_FILE="$SCRIPT_DIR/.env"
REQ_FILE="$SCRIPT_DIR/requirements.txt"
CONFIG_PATH="$SCRIPT_DIR/config.yml"
DEBUG="${DEBUG:-0}"
DEFAULT_ENV_NAME="production"
DEFAULT_ALL_PATH="/"

log_debug() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] $*"
  fi
}

step() {
  local msg="$1"
  echo "==> ${msg}"
}

step "Starting Infisical export for Cloudflare Tunnel"
step "Checking prerequisites"
require_ubuntu
require_cmd curl
step "curl found: $(command -v curl)"
if command -v jq >/dev/null 2>&1; then
  step "jq found: $(command -v jq)"
else
  step "jq not found; will use python3 if available"
  require_cmd python3
fi

step "Collecting project and auth details"
PROJECT_ID_DEFAULT="dce03ebf-dea5-47a3-8893-d1779dcfbbac"
read -r -p "Infisical Project ID [Default (Homelab project): ${PROJECT_ID_DEFAULT}]: " PROJECT_ID
if [[ -z "${PROJECT_ID// }" ]]; then
  PROJECT_ID="$PROJECT_ID_DEFAULT"
fi

read -r -s -p "Infisical Token: " INFISICAL_TOKEN
if [[ -z "${INFISICAL_TOKEN// }" ]]; then
  echo -e "\nERROR: Token is required." >&2
  exit 1
fi

echo ""

ENV_NAME="prod"
read -r -p "Environment slug [Default: ${ENV_NAME}]: " ENV_INPUT
if [[ -n "${ENV_INPUT// }" ]]; then
  ENV_NAME="$ENV_INPUT"
fi

read -r -p "Infisical API URL (leave blank for default): " API_INPUT
if [[ -n "${API_INPUT// }" ]]; then
  INFISICAL_API_URL="$API_INPUT"
fi
INFISICAL_API_URL="${INFISICAL_API_URL:-https://app.infisical.com/api}"
log_debug "Project ID: ${PROJECT_ID}"
log_debug "Environment: ${ENV_NAME}"
log_debug "Output file: ${OUTPUT_FILE}"
log_debug "API URL: ${INFISICAL_API_URL:-<default>}"
step "Using settings"
echo "Project ID: ${PROJECT_ID}"
echo "Environment: ${ENV_NAME}"
echo "Output file: ${OUTPUT_FILE}"
if [[ -n "${INFISICAL_API_URL:-}" ]]; then
  echo "API URL: ${INFISICAL_API_URL}"
else
  echo "API URL: <default>"
fi

step "Preparing output"
tmp_output=$(mktemp)
cleanup() {
  rm -f "$tmp_output"
}
trap cleanup EXIT

fetch_api() {
  local path="$1"
  local recursive="$2"
  curl -sS -G "${INFISICAL_API_URL}/v4/secrets" \
    -H "Authorization: Bearer ${INFISICAL_TOKEN}" \
    --data-urlencode "projectId=${PROJECT_ID}" \
    --data-urlencode "environment=${ENV_NAME}" \
    --data-urlencode "secretPath=${path}" \
    --data-urlencode "recursive=${recursive}" \
    --data-urlencode "include_imports=true" \
    --data-urlencode "viewSecretValue=true"
}

write_env_from_response() {
  local response="$1"
  local include_path_comments="$2"
  local mode="$3" # "write" or "append"
  local temp_file
  temp_file=$(mktemp)
  if command -v jq >/dev/null 2>&1; then
    if [[ "$include_path_comments" == "1" ]]; then
      printf "%s\n" "$response" | jq -r '
        .secrets
        | sort_by(.secretPath // .secretPath // "")
        | group_by(.secretPath // .secretPath // "")
        | .[]
        | (if (.[0].secretPath // .secretPath // "") != "" then "# path: \(.[0].secretPath // .secretPath)" else "# path: /" end),
          (.[] | "\(.secretKey)=\(.secretValue)")' > "$temp_file"
    else
      printf "%s\n" "$response" | jq -r '.secrets[] | "\(.secretKey)=\(.secretValue)"' > "$temp_file"
    fi
  else
    if [[ "$include_path_comments" == "1" ]]; then
      printf "%s\n" "$response" | python3 - <<'PY' > "$temp_file"
import json, sys
data = sys.stdin.read().strip()
obj = json.loads(data)
secrets = obj.get("secrets", [])
def get_path(s):
    return s.get("secretPath") or "/"
secrets.sort(key=get_path)
last_path = None
for s in secrets:
    path = get_path(s)
    if path != last_path:
        print(f"# path: {path}")
        last_path = path
    key = s.get("secretKey", "")
    val = s.get("secretValue", "")
    if key:
        print(f"{key}={val}")
PY
    else
      printf "%s\n" "$response" | python3 - <<'PY' > "$temp_file"
import json, sys
data = sys.stdin.read().strip()
obj = json.loads(data)
for s in obj.get("secrets", []):
    key = s.get("secretKey", "")
    val = s.get("secretValue", "")
    if key:
        print(f"{key}={val}")
PY
    fi
  fi
  if [[ "$mode" == "append" ]]; then
    cat "$temp_file" >> "$tmp_output"
  else
    cat "$temp_file" > "$tmp_output"
  fi
  rm -f "$temp_file"
}

read -r -p "Fetch all variables from root (${DEFAULT_ALL_PATH}) and subfolders? [y/N]: " FETCH_ALL
FETCH_ALL=$(printf "%s" "$FETCH_ALL" | tr '[:upper:]' '[:lower:]')

if [[ "$FETCH_ALL" == "y" || "$FETCH_ALL" == "yes" ]]; then
  step "Mode: export all folders from root (recursive)"
  response=$(fetch_api "$DEFAULT_ALL_PATH" "true")
  : > "$tmp_output"
  write_env_from_response "$response" "1" "write"
else
  step "Mode: export a specific folder"
  read -r -p "Enter folder path(s) (comma-separated, e.g. /cloudflare): " PATH_NAME
  if [[ -z "${PATH_NAME// }" ]]; then
    echo "ERROR: Folder path is required." >&2
    exit 1
  fi
  IFS=',' read -r -a path_list <<< "$PATH_NAME"
  : > "$tmp_output"
  for p in "${path_list[@]}"; do
    p="${p//[[:space:]]/}"
    if [[ -z "$p" ]]; then
      continue
    fi
    step "Exporting selected folder: ${p}"
    response=$(fetch_api "$p" "false")
    write_env_from_response "$response" "1" "append"
  done
fi

if [[ ! -s "$tmp_output" ]]; then
  echo "ERROR: No secrets were exported. The .env file would be empty." >&2
  echo "Check: project ID, token permissions, environment slug, and folder path." >&2
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] Output file is empty: $tmp_output" >&2
  fi
  exit 1
fi

step "Writing output file"
escape_env() {
  local val="$1"
  val="${val//\\/\\\\}"
  val="${val//\"/\\\"}"
  printf '%s' "$val"
}

get_env_val() {
  local key="$1"
  local file="$2"
  awk -F= -v k="$key" '
    $1==k { sub(/^[^=]*=/,""); print; exit }
  ' "$file"
}

existing_token=""
existing_id=""
if [[ -f "$OUTPUT_FILE" ]]; then
  existing_token="$(get_env_val "CLOUDFLARE_TUNNEL_TOKEN" "$OUTPUT_FILE")"
  existing_id="$(get_env_val "CLOUDFLARE_TUNNEL_ID" "$OUTPUT_FILE")"
fi

{
  while IFS= read -r line || [[ -n "$line" ]]; do
    if [[ -z "${line// }" || "${line:0:1}" == "#" ]]; then
      echo "$line"
      continue
    fi
    key="${line%%=*}"
    val="${line#*=}"
    printf '%s="%s"\n' "$key" "$(escape_env "$val")"
  done < "$tmp_output"
} > "$OUTPUT_FILE"

# Preserve existing token/id if Infisical did not return them
if ! grep -qE '^CLOUDFLARE_TUNNEL_TOKEN=' "$OUTPUT_FILE" && [[ -n "$existing_token" ]]; then
  printf 'CLOUDFLARE_TUNNEL_TOKEN="%s"\n' "$(escape_env "$existing_token")" >> "$OUTPUT_FILE"
fi
if ! grep -qE '^CLOUDFLARE_TUNNEL_ID=' "$OUTPUT_FILE" && [[ -n "$existing_id" ]]; then
  printf 'CLOUDFLARE_TUNNEL_ID="%s"\n' "$(escape_env "$existing_id")" >> "$OUTPUT_FILE"
fi

# Ensure pinned defaults exist
if [[ -f "$REQ_FILE" ]]; then
  while IFS='=' read -r key val; do
    [[ -z "${key// }" || "${key:0:1}" == "#" ]] && continue
    key="$(echo "$key" | xargs)"
    val="$(echo "${val-}" | xargs)"
    if ! grep -qE "^${key}=" "$OUTPUT_FILE"; then
      printf '%s="%s"\n' "$key" "$(escape_env "$val")" >> "$OUTPUT_FILE"
    fi
  done < "$REQ_FILE"
fi

if ! grep -qE '^CLOUDFLARE_CONFIG_PATH=' "$OUTPUT_FILE"; then
  printf 'CLOUDFLARE_CONFIG_PATH="%s"\n' "$(escape_env "$CONFIG_PATH")" >> "$OUTPUT_FILE"
fi
if ! grep -qE '^CLOUDFLARE_APP_NETWORK=' "$OUTPUT_FILE"; then
  printf 'CLOUDFLARE_APP_NETWORK="%s"\n' "$(escape_env "appnet")" >> "$OUTPUT_FILE"
fi

chmod 600 "$OUTPUT_FILE"

step "Done"
echo "Wrote: $OUTPUT_FILE"
