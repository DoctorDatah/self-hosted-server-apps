#!/usr/bin/env bash
set -euo pipefail

# Validates Infisical access by exporting secrets from all folders and writing a combined output file.

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  fi
}

step() {
  local msg="$1"
  echo "==> ${msg}"
}

timeout_cmd() {
  if command -v timeout >/dev/null 2>&1; then
    echo "timeout"
  elif command -v gtimeout >/dev/null 2>&1; then
    echo "gtimeout"
  else
    echo ""
  fi
}

run_with_timeout() {
  local seconds="$1"
  shift
  local tcmd
  tcmd="$(timeout_cmd)"
  if [[ -n "$tcmd" ]]; then
    "$tcmd" "$seconds" "$@"
  else
    "$@"
  fi
}

require_cmd curl

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONFIG_FILE="$SCRIPT_DIR/infisical.local.env"
OUTPUT_FILE="$SCRIPT_DIR/variable_exported_all.txt"

step "Loading local config"
if [[ -f "$CONFIG_FILE" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "$CONFIG_FILE"
  set +a
else
  echo "ERROR: Missing config file: $CONFIG_FILE" >&2
  exit 1
fi

PROJECT_ID="${INFISICAL_PROJECT_ID:-}"
ENV_NAME="${INFISICAL_ENV:-}"
TOKEN_FROM_FILE="${INFISICAL_TOKEN:-}"
ROOT_PATH="${INFISICAL_ROOT_PATH:-/}"
API_BASE="${INFISICAL_API_URL:-https://app.infisical.com/api}"

step "Validating config values"
if [[ -z "${PROJECT_ID// }" ]]; then
  echo "ERROR: INFISICAL_PROJECT_ID is required in $CONFIG_FILE" >&2
  exit 1
fi
if [[ -z "${TOKEN_FROM_FILE// }" ]]; then
  echo "ERROR: INFISICAL_TOKEN is required in $CONFIG_FILE" >&2
  exit 1
fi
if [[ -z "${ENV_NAME// }" ]]; then
  echo "ERROR: INFISICAL_ENV is required in $CONFIG_FILE" >&2
  exit 1
fi

step "Exporting secrets (recursive) from ${ROOT_PATH}"
: > "$OUTPUT_FILE"

response=$(run_with_timeout 20 curl -sS -G "${API_BASE}/v4/secrets" \
  -H "Authorization: Bearer ${TOKEN_FROM_FILE}" \
  --data-urlencode "projectId=${PROJECT_ID}" \
  --data-urlencode "environment=${ENV_NAME}" \
  --data-urlencode "secretPath=${ROOT_PATH}" \
  --data-urlencode "recursive=true" \
  --data-urlencode "include_imports=true" \
  --data-urlencode "viewSecretValue=true")

if [[ -z "${response// }" ]]; then
  echo "ERROR: Empty response from API. Check token, project, env, and API URL." >&2
  exit 1
fi

if command -v jq >/dev/null 2>&1; then
  printf "%s\n" "$response" | jq -r '.secrets[] | "\(.secretKey)=\(.secretValue)"' > "$OUTPUT_FILE"
elif command -v python3 >/dev/null 2>&1; then
  printf "%s\n" "$response" | python3 - <<'PY' > "$OUTPUT_FILE"
import json, sys
data = sys.stdin.read().strip()
obj = json.loads(data)
for s in obj.get("secrets", []):
    key = s.get("secretKey", "")
    val = s.get("secretValue", "")
    if key:
        print(f"{key}={val}")
PY
else
  echo "ERROR: Missing jq or python3 to parse API response." >&2
  exit 1
fi

if [[ ! -s "$OUTPUT_FILE" ]]; then
  echo "ERROR: Export succeeded but returned no secrets." >&2
  exit 1
fi

count=$(awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{c++} END{print c+0}' "$OUTPUT_FILE")
echo "Secrets found: $count"
echo "Wrote: $OUTPUT_FILE"
