#!/usr/bin/env bash
set -euo pipefail

# Fetches secrets from Infisical and writes a .env file in the VMs folder.

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  fi
}

require_cmd infisical

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VM_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
OUTPUT_FILE="$VM_DIR/.env"
DEBUG="${DEBUG:-0}"

log_debug() {
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] $*"
  fi
}

read -r -p "Infisical Project ID: " PROJECT_ID
if [[ -z "${PROJECT_ID// }" ]]; then
  echo "ERROR: Project ID is required." >&2
  exit 1
fi

read -r -s -p "Infisical Token: " INFISICAL_TOKEN
if [[ -z "${INFISICAL_TOKEN// }" ]]; then
  echo -e "\nERROR: Token is required." >&2
  exit 1
fi

echo ""

ENV_NAME="production"
read -r -p "Environment slug [${ENV_NAME}]: " ENV_INPUT
if [[ -n "${ENV_INPUT// }" ]]; then
  ENV_NAME="$ENV_INPUT"
fi

export INFISICAL_TOKEN
export INFISICAL_DISABLE_UPDATE_CHECK=true
INFISICAL_API_URL="${INFISICAL_API_URL:-}"
log_debug "Project ID: ${PROJECT_ID}"
log_debug "Environment: ${ENV_NAME}"
log_debug "Output file: ${OUTPUT_FILE}"
log_debug "API URL: ${INFISICAL_API_URL:-<default>}"

tmp_dir=$(mktemp -d)
tmp_file="$tmp_dir/export.env"
combined_file="$tmp_dir/combined.env"
cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

list_folders() {
  local path="$1"
  set +e
  infisical secrets folders get --path="$path" --env="$ENV_NAME" --projectId="$PROJECT_ID" --token="$INFISICAL_TOKEN"
  local status=$?
  if [[ $status -ne 0 ]]; then
    infisical secrets folders get --path="$path" --env="$ENV_NAME" --token="$INFISICAL_TOKEN"
    status=$?
  fi
  set -e
  return $status
}

export_with_fallback() {
  local path="$1"
  local out_file="$2"
  set +e
  infisical export \
    --projectId="$PROJECT_ID" \
    --env="$ENV_NAME" \
    --path="$path" \
    --include-imports \
    --format=dotenv \
    --output-file="$out_file"
  local status=$?
  if [[ $status -ne 0 ]]; then
    infisical export \
      --projectId="$PROJECT_ID" \
      --env="$ENV_NAME" \
      --path="$path" \
      --format=dotenv \
      --output-file="$out_file"
    status=$?
  fi
  set -e
  return $status
}

extract_paths_from_output() {
  if command -v python3 >/dev/null 2>&1; then
    python3 - <<'PY' || true
import json, sys
data = sys.stdin.read().strip()
if not data:
    sys.exit(0)
try:
    obj = json.loads(data)
except Exception:
    sys.exit(0)
paths = []
def walk(x):
    if isinstance(x, dict):
        for k, v in x.items():
            if k == "path" and isinstance(v, str) and v.startswith("/"):
                paths.append(v)
            walk(v)
    elif isinstance(x, list):
        for i in x:
            walk(i)
walk(obj)
for p in paths:
    print(p)
PY
  fi
}

get_folder_paths() {
  local path="$1"
  local output=""
  output=$(infisical secrets folders get --path="$path" --env="$ENV_NAME" --projectId="$PROJECT_ID" --token="$INFISICAL_TOKEN" 2>/dev/null || true)
  if [[ -z "$output" ]]; then
    output=$(infisical secrets folders get --path="$path" --env="$ENV_NAME" --token="$INFISICAL_TOKEN" 2>/dev/null || true)
  fi
  log_debug "folders.get raw output for ${path}: ${output:-<empty>}"

  local parsed=""
  parsed=$(printf "%s" "$output" | extract_paths_from_output || true)
  if [[ -n "$parsed" ]]; then
    printf "%s\n" "$parsed" | sort -u
    return 0
  fi

  printf "%s\n" "$output" | grep -Eo '/[^[:space:]]+' | sort -u
}

collect_all_folders() {
  local -a queue=("/")
  declare -A seen
  seen["/"]=1
  while [[ ${#queue[@]} -gt 0 ]]; do
    local current="${queue[0]}"
    queue=("${queue[@]:1}")
    mapfile -t children < <(get_folder_paths "$current")
    for child in "${children[@]}"; do
      if [[ -z "${seen[$child]+x}" ]]; then
        seen["$child"]=1
        queue+=("$child")
      fi
    done
  done

  for key in "${!seen[@]}"; do
    if [[ "$key" != "/" ]]; then
      printf "%s\n" "$key"
    fi
  done | sort -u
}

append_exports_for_path() {
  local path="$1"
  local out_file="$2"
  : > "$out_file"
  log_debug "Exporting path: ${path}"
  export_with_fallback "$path" "$out_file" || return 1
  if [[ -s "$out_file" ]]; then
    log_debug "Exported bytes for ${path}: $(wc -c < "$out_file" | tr -d ' ')"
    cat "$out_file" >> "$combined_file"
    printf "\n" >> "$combined_file"
  else
    log_debug "No secrets found at ${path}"
  fi
  return 0
}

read -r -p "Fetch all variables (root path / and subfolders)? [y/N]: " FETCH_ALL
FETCH_ALL=${FETCH_ALL,,}

if [[ "$FETCH_ALL" == "y" || "$FETCH_ALL" == "yes" ]]; then
  : > "$combined_file"
  append_exports_for_path "/" "$tmp_file"
  mapfile -t all_folders < <(collect_all_folders)
  for folder in "${all_folders[@]}"; do
    append_exports_for_path "$folder" "$tmp_file"
  done
else
  echo "Available folders (root = /):"
  if ! list_folders "/"; then
    echo "WARNING: Could not list folders. You can still enter a path manually." >&2
  fi
  echo ""
  read -r -p "Enter folder path (e.g. /cloudflare): " PATH_NAME
  if [[ -z "${PATH_NAME// }" ]]; then
    echo "ERROR: Folder path is required." >&2
    exit 1
  fi
  : > "$combined_file"
  append_exports_for_path "$PATH_NAME" "$tmp_file"
fi

if [[ ! -s "$combined_file" ]]; then
  echo "ERROR: No secrets were exported. The .env file would be empty." >&2
  echo "Check: project ID, token permissions, environment slug, and folder path." >&2
  if [[ "$DEBUG" == "1" ]]; then
    echo "[DEBUG] Combined file is empty: $combined_file" >&2
  fi
  exit 1
fi

echo "Fetched variables:"
awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{print " - " $1}' "$combined_file"

mv "$combined_file" "$OUTPUT_FILE"
chmod 600 "$OUTPUT_FILE"

echo "Wrote: $OUTPUT_FILE"
