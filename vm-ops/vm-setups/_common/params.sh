#!/usr/bin/env bash
# Shared helpers for stage scripts.

vmcx_param_get() {
  local key="$1"
  local default_value="${2-}"
  local payload="${VMCX_PARAMS_JSON:-}"
  if [[ -z "$payload" ]]; then
    payload='{}'
  fi

  if command -v python3 >/dev/null 2>&1; then
    python3 - "$payload" "$key" "$default_value" <<'PY'
import json
import sys

raw = sys.argv[1] if len(sys.argv) > 1 else "{}"
key = sys.argv[2] if len(sys.argv) > 2 else ""
default = sys.argv[3] if len(sys.argv) > 3 else ""

try:
    data = json.loads(raw or "{}")
except Exception:
    data = {}

value = data.get(key, default)
if isinstance(value, bool):
    print("true" if value else "false")
elif value is None:
    print(default)
elif isinstance(value, list):
    print(",".join(str(x) for x in value))
else:
    print(str(value))
PY
    return
  fi

  printf '%s\n' "$default_value"
}

vmcx_param_bool() {
  local key="$1"
  local default_value="${2:-false}"
  local value
  local value_lc
  local default_lc
  value="$(vmcx_param_get "$key" "$default_value")"
  value_lc="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"
  default_lc="$(printf '%s' "$default_value" | tr '[:upper:]' '[:lower:]')"
  case "$value_lc" in
    1|true|yes|y|on) printf 'true\n' ;;
    0|false|no|n|off) printf 'false\n' ;;
    *)
      if [[ "$default_lc" =~ ^(1|true|yes|y|on)$ ]]; then
        printf 'true\n'
      else
        printf 'false\n'
      fi
      ;;
  esac
}

vmcx_require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: Missing required command: $cmd" >&2
    exit 1
  fi
}

vmcx_run_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "ERROR: Command requires root or sudo: $*" >&2
    exit 1
  fi
}

vmcx_is_linux() {
  [[ "$(uname -s)" == "Linux" ]]
}
