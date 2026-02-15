#!/usr/bin/env bash
set -euo pipefail

# Validates Infisical token/project/env by attempting a minimal export.

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

require_cmd infisical

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
CONFIG_FILE="$SCRIPT_DIR/infisical.local.env"

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
ENV_NAME="${INFISICAL_ENV:-production}"
DEFAULT_PATH="${INFISICAL_PATH:-/}"
TOKEN_FROM_FILE="${INFISICAL_TOKEN:-}"

step "Collecting values from local config"
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

TEST_PATH="$DEFAULT_PATH"

export INFISICAL_TOKEN="$TOKEN_FROM_FILE"
export INFISICAL_DISABLE_UPDATE_CHECK=true

step "Validating access (project/env/path)"
set +e
export_output=$(run_with_timeout 15 infisical export \
  --projectId="$PROJECT_ID" \
  --env="$ENV_NAME" \
  --path="$TEST_PATH" \
  --format=dotenv)
status=$?
set -e

if [[ $status -ne 0 ]]; then
  echo "ERROR: Infisical export failed (exit $status)." >&2
  exit 1
fi

if [[ -z "${export_output// }" ]]; then
  echo "ERROR: Export succeeded but returned no secrets." >&2
  echo "Check: token permissions, environment slug, and folder path." >&2
  exit 1
fi

step "Success"
count=$(printf "%s\n" "$export_output" | awk -F= '/^[A-Za-z_][A-Za-z0-9_]*=/{c++} END{print c+0}')
echo "Secrets found: $count"

output_file="$SCRIPT_DIR/variable_exported_test.txt"
printf "%s\n" "$export_output" > "$output_file"
echo "Wrote: $output_file"
