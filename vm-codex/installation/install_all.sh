#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPTS_DIR="$SCRIPT_DIR/scripts"
PROFILES_DIR="$SCRIPT_DIR/profiles"
SCHEMA_FILE="$PROFILES_DIR/schema.yaml"
VERSIONS_FILE="$SCRIPT_DIR/requirements/versions.yaml"
STATE_DIR="$SCRIPT_DIR/.state"
LOG_DIR="$SCRIPT_DIR/logs"

PROFILE=""
ONLY=""
DRY_RUN=0
RESUME=0
LIST_PROFILES=0
LIST_TOOLS=0
LOCK_DIR=""
LOG_FILE=""
STATE_FILE=""
STARTED_AT=""

PROFILE_NAME=""
PROFILE_DESCRIPTION=""
PROFILE_OS_FAMILY=""
PROFILE_OS_VERSION_CONSTRAINTS=""

PROFILE_TOOLS=()
FINAL_TOOLS=()
REQUIRED_BINARIES=()
REQUIRED_ENV_VARS=()
COMPLETED_TOOLS=()
SELECTED_TOOLS=()
REQUIRED_TOOLS=()
VISITING_TOOLS=()
VERSION_KEYS=()
VERSION_VALUES=()

show_usage() {
  cat <<'USAGE'
Usage: ./install_all.sh --profile <name> [options]

Options:
  --profile <name>      Profile name from profiles/<name>.yaml
  --only <a,b,c>        Install only selected tools (dependency closure is auto-added)
  --list-profiles       List available profiles
  --list-tools          List available tool scripts
  --dry-run             Print planned actions without executing installers
  --resume              Resume from .state/<profile>.json
  -h, --help            Show this help
USAGE
}

cleanup_lock() {
  if [[ -n "$LOCK_DIR" && -d "$LOCK_DIR" ]]; then
    rm -rf "$LOCK_DIR"
  fi
}

trap cleanup_lock EXIT

array_contains() {
  local needle="$1"
  shift
  local item
  for item in "$@"; do
    if [[ "$item" == "$needle" ]]; then
      return 0
    fi
  done
  return 1
}

set_version() {
  local key="$1"
  local value="$2"
  local i
  for i in "${!VERSION_KEYS[@]}"; do
    if [[ "${VERSION_KEYS[$i]}" == "$key" ]]; then
      VERSION_VALUES[$i]="$value"
      return 0
    fi
  done
  VERSION_KEYS+=("$key")
  VERSION_VALUES+=("$value")
}

get_version() {
  local key="$1"
  local i
  for i in "${!VERSION_KEYS[@]}"; do
    if [[ "${VERSION_KEYS[$i]}" == "$key" ]]; then
      printf '%s' "${VERSION_VALUES[$i]}"
      return 0
    fi
  done
  printf ''
}

dependency_for_tool() {
  case "$1" in
    docker) printf 'utils' ;;
    network) printf 'docker' ;;
    codex) printf 'utils' ;;
    infisical) printf 'utils' ;;
    *) printf '' ;;
  esac
}

list_profiles() {
  if [[ ! -d "$PROFILES_DIR" ]]; then
    return 0
  fi
  local found=0
  while IFS= read -r file; do
    found=1
    basename "$file" .yaml
  done < <(find "$PROFILES_DIR" -maxdepth 1 -type f -name '*.yaml' ! -name 'schema.yaml' | sort)
  if [[ $found -eq 0 ]]; then
    echo "No profiles found in $PROFILES_DIR"
  fi
}

list_tools() {
  local found=0
  while IFS= read -r file; do
    found=1
    basename "$file" .sh
  done < <(find "$SCRIPTS_DIR" -maxdepth 1 -type f -name '*.sh' | sort)
  if [[ $found -eq 0 ]]; then
    echo "No tool scripts found in $SCRIPTS_DIR"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --profile)
        shift
        PROFILE="${1-}"
        ;;
      --only)
        shift
        ONLY="${1-}"
        ;;
      --list-profiles)
        LIST_PROFILES=1
        ;;
      --list-tools)
        LIST_TOOLS=1
        ;;
      --dry-run)
        DRY_RUN=1
        ;;
      --resume)
        RESUME=1
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
}

acquire_lock() {
  local lock_name="vm-installations-${PROFILE}"
  LOCK_DIR="/tmp/${lock_name}.lock"
  if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Another installation run is active for profile '$PROFILE' (lock: $LOCK_DIR)." >&2
    exit 1
  fi
  echo "$$" > "$LOCK_DIR/pid"
}

setup_logging() {
  mkdir -p "$LOG_DIR"
  local stamp
  stamp=$(date -u +"%Y%m%dT%H%M%SZ")
  LOG_FILE="$LOG_DIR/${stamp}-${PROFILE}.log"
  exec > >(tee -a "$LOG_FILE") 2>&1
}

require_file() {
  local path="$1"
  local label="$2"
  if [[ ! -f "$path" ]]; then
    echo "Missing $label: $path" >&2
    exit 1
  fi
}

load_profile_payload() {
  local profile_file="$PROFILES_DIR/${PROFILE}.yaml"
  require_file "$SCHEMA_FILE" "schema file"
  require_file "$VERSIONS_FILE" "versions file"
  require_file "$profile_file" "profile file"
  require_file "$SCRIPTS_DIR/profile_helper.py" "profile helper"

  local payload
  payload=$(python3 "$SCRIPTS_DIR/profile_helper.py" \
    --schema-file "$SCHEMA_FILE" \
    --profile-file "$profile_file" \
    --versions-file "$VERSIONS_FILE")

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    case "$line" in
      PROFILE_NAME=*) PROFILE_NAME="${line#PROFILE_NAME=}" ;;
      PROFILE_DESCRIPTION=*) PROFILE_DESCRIPTION="${line#PROFILE_DESCRIPTION=}" ;;
      OS_FAMILY=*) PROFILE_OS_FAMILY="${line#OS_FAMILY=}" ;;
      OS_VERSION_CONSTRAINTS=*) PROFILE_OS_VERSION_CONSTRAINTS="${line#OS_VERSION_CONSTRAINTS=}" ;;
      TOOL::*) PROFILE_TOOLS+=("${line#TOOL::}") ;;
      BIN::*) REQUIRED_BINARIES+=("${line#BIN::}") ;;
      ENV::*) REQUIRED_ENV_VARS+=("${line#ENV::}") ;;
      VER::*)
        local rest="${line#VER::}"
        local key="${rest%%::*}"
        local value="${rest#*::}"
        set_version "$key" "$value"
        ;;
      *)
        echo "Unexpected payload line: $line" >&2
        exit 1
        ;;
    esac
  done < <(python3 - "$payload" <<'PY'
import json
import sys

payload = json.loads(sys.argv[1])
print(f"PROFILE_NAME={payload['name']}")
print(f"PROFILE_DESCRIPTION={payload.get('description', '')}")
print(f"OS_FAMILY={payload['os_family']}")
print(f"OS_VERSION_CONSTRAINTS={payload['os_version_constraints']}")
for item in payload['tools']:
    print(f"TOOL::{item}")
for item in payload.get('required_binaries', []):
    print(f"BIN::{item}")
for item in payload.get('required_env_vars', []):
    print(f"ENV::{item}")
for key, value in payload.get('tool_versions', {}).items():
    print(f"VER::{key}::{value}")
PY
)

  if [[ ${#PROFILE_TOOLS[@]} -eq 0 ]]; then
    echo "Profile '$PROFILE' has no tools." >&2
    exit 1
  fi

  local tool
  for tool in "${PROFILE_TOOLS[@]}"; do
    if [[ ! -f "$SCRIPTS_DIR/${tool}.sh" ]]; then
      echo "Profile '$PROFILE' references missing tool script: $SCRIPTS_DIR/${tool}.sh" >&2
      exit 1
    fi
  done
}

compare_versions() {
  local lhs="$1"
  local op="$2"
  local rhs="$3"

  if command -v dpkg >/dev/null 2>&1; then
    case "$op" in
      '>') dpkg --compare-versions "$lhs" gt "$rhs" ;;
      '>=') dpkg --compare-versions "$lhs" ge "$rhs" ;;
      '<') dpkg --compare-versions "$lhs" lt "$rhs" ;;
      '<=') dpkg --compare-versions "$lhs" le "$rhs" ;;
      '=='|'=') dpkg --compare-versions "$lhs" eq "$rhs" ;;
      *) return 1 ;;
    esac
    return $?
  fi

  case "$op" in
    '>=') [[ "$(printf '%s\n%s\n' "$rhs" "$lhs" | sort -V | tail -n1)" == "$lhs" ]] ;;
    '<=') [[ "$(printf '%s\n%s\n' "$lhs" "$rhs" | sort -V | tail -n1)" == "$rhs" ]] ;;
    '>') [[ "$lhs" != "$rhs" && "$(printf '%s\n%s\n' "$rhs" "$lhs" | sort -V | tail -n1)" == "$lhs" ]] ;;
    '<') [[ "$lhs" != "$rhs" && "$(printf '%s\n%s\n' "$lhs" "$rhs" | sort -V | tail -n1)" == "$rhs" ]] ;;
    '=='|'=') [[ "$lhs" == "$rhs" ]] ;;
    *) return 1 ;;
  esac
}

check_os_preflight() {
  if [[ ! -f /etc/os-release ]]; then
    echo "Cannot perform OS check: /etc/os-release missing" >&2
    exit 1
  fi

  # shellcheck disable=SC1091
  source /etc/os-release

  local normalized_family
  normalized_family="$(printf '%s' "$PROFILE_OS_FAMILY" | tr '[:upper:]' '[:lower:]')"

  case "$normalized_family" in
    debian)
      if [[ "${ID:-}" != "debian" && "${ID:-}" != "ubuntu" && " ${ID_LIKE:-} " != *" debian "* ]]; then
        echo "Profile '$PROFILE' requires debian family; found ID='${ID:-unknown}' ID_LIKE='${ID_LIKE:-unknown}'." >&2
        exit 1
      fi
      ;;
    ubuntu)
      if [[ "${ID:-}" != "ubuntu" ]]; then
        echo "Profile '$PROFILE' requires ubuntu; found ID='${ID:-unknown}'." >&2
        exit 1
      fi
      ;;
    *)
      echo "Unsupported os_family in profile: $PROFILE_OS_FAMILY" >&2
      exit 1
      ;;
  esac

  local constraint="${PROFILE_OS_VERSION_CONSTRAINTS// /}"
  if [[ -n "$constraint" ]]; then
    if [[ ! "$constraint" =~ ^(>=|<=|==|=|>|<)([A-Za-z0-9._-]+)$ ]]; then
      echo "Invalid os_version_constraints: $PROFILE_OS_VERSION_CONSTRAINTS" >&2
      exit 1
    fi
    local op="${BASH_REMATCH[1]}"
    local expected="${BASH_REMATCH[2]}"
    local current="${VERSION_ID:-}"
    if [[ -z "$current" ]]; then
      echo "Cannot determine VERSION_ID from /etc/os-release" >&2
      exit 1
    fi
    if ! compare_versions "$current" "$op" "$expected"; then
      echo "OS version check failed: current=$current expected '$op $expected'" >&2
      exit 1
    fi
  fi
}

check_binaries_preflight() {
  local bin
  for bin in "${REQUIRED_BINARIES[@]}"; do
    if ! command -v "$bin" >/dev/null 2>&1; then
      echo "Missing required binary for profile '$PROFILE': $bin" >&2
      exit 1
    fi
  done
}

check_env_preflight() {
  local env_name
  for env_name in "${REQUIRED_ENV_VARS[@]}"; do
    if [[ -z "${!env_name-}" ]]; then
      echo "Required environment variable is unset: $env_name" >&2
      exit 1
    fi
  done
}

parse_only_tools() {
  if [[ -z "$ONLY" ]]; then
    return 0
  fi
  IFS=',' read -r -a SELECTED_TOOLS <<< "$ONLY"
  local i
  for i in "${!SELECTED_TOOLS[@]}"; do
    SELECTED_TOOLS[$i]="${SELECTED_TOOLS[$i]// /}"
    if [[ -z "${SELECTED_TOOLS[$i]}" ]]; then
      echo "Invalid empty value in --only list" >&2
      exit 1
    fi
  done
}

profile_contains_tool() {
  array_contains "$1" "${PROFILE_TOOLS[@]}"
}

mark_required_tool() {
  local tool="$1"
  if array_contains "$tool" "${VISITING_TOOLS[@]}"; then
    echo "Dependency cycle detected at tool '$tool'" >&2
    exit 1
  fi
  if array_contains "$tool" "${REQUIRED_TOOLS[@]}"; then
    return 0
  fi
  if ! profile_contains_tool "$tool"; then
    echo "Tool '$tool' is not in profile '$PROFILE'" >&2
    exit 1
  fi

  VISITING_TOOLS+=("$tool")
  local dep
  dep=$(dependency_for_tool "$tool")
  if [[ -n "$dep" ]]; then
    mark_required_tool "$dep"
  fi

  local next_visiting=()
  local t
  for t in "${VISITING_TOOLS[@]}"; do
    if [[ "$t" != "$tool" ]]; then
      next_visiting+=("$t")
    fi
  done
  VISITING_TOOLS=("${next_visiting[@]:-}")

  REQUIRED_TOOLS+=("$tool")
}

resolve_final_tools() {
  if [[ ${#SELECTED_TOOLS[@]} -eq 0 ]]; then
    FINAL_TOOLS=("${PROFILE_TOOLS[@]}")
    return 0
  fi

  local selected
  for selected in "${SELECTED_TOOLS[@]}"; do
    if ! profile_contains_tool "$selected"; then
      echo "Unknown tool for profile '$PROFILE': $selected" >&2
      exit 1
    fi
    mark_required_tool "$selected"
  done

  local tool
  for tool in "${PROFILE_TOOLS[@]}"; do
    if array_contains "$tool" "${REQUIRED_TOOLS[@]}"; then
      FINAL_TOOLS+=("$tool")
    fi
  done
}

state_write() {
  local failed_tool="${1-}"
  local completed_joined=""
  local item
  for item in "${COMPLETED_TOOLS[@]}"; do
    if [[ -z "$completed_joined" ]]; then
      completed_joined="$item"
    else
      completed_joined="$completed_joined,$item"
    fi
  done

  python3 - "$STATE_FILE" "$PROFILE" "$STARTED_AT" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$failed_tool" "$completed_joined" <<'PY'
import json
import sys
from pathlib import Path

state_file = Path(sys.argv[1])
profile = sys.argv[2]
started = sys.argv[3]
updated = sys.argv[4]
failed_tool = sys.argv[5]
completed = [x for x in sys.argv[6].split(',') if x]

existing = {}
if state_file.exists():
    existing = json.loads(state_file.read_text(encoding="utf-8"))

versions = existing.get("tool_versions", {})
payload = {
    "profile": profile,
    "last_run_started_at": started,
    "last_updated_at": updated,
    "failed_tool": failed_tool,
    "completed_tools": completed,
    "tool_versions": versions,
}
state_file.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
PY
}

state_set_versions() {
  local pairs=""
  local i
  for i in "${!VERSION_KEYS[@]}"; do
    if [[ -n "$pairs" ]]; then
      pairs+=$'\n'
    fi
    pairs+="${VERSION_KEYS[$i]}=${VERSION_VALUES[$i]}"
  done

  python3 - "$STATE_FILE" "$pairs" <<'PY'
import json
import sys
from pathlib import Path

state_file = Path(sys.argv[1])
raw = sys.argv[2]
versions = {}
if raw:
    for line in raw.splitlines():
        if not line.strip() or '=' not in line:
            continue
        key, value = line.split('=', 1)
        versions[key] = value

existing = {}
if state_file.exists():
    existing = json.loads(state_file.read_text(encoding="utf-8"))
existing["tool_versions"] = versions
state_file.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
PY
}

state_load_resume() {
  if [[ $RESUME -ne 1 ]]; then
    return 0
  fi
  if [[ ! -f "$STATE_FILE" ]]; then
    echo "--resume requested but no state file found at $STATE_FILE" >&2
    exit 1
  fi

  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    COMPLETED_TOOLS+=("$line")
  done < <(python3 - "$STATE_FILE" <<'PY'
import json
import sys
from pathlib import Path

state_file = Path(sys.argv[1])
payload = json.loads(state_file.read_text(encoding="utf-8"))
for tool in payload.get("completed_tools", []):
    print(tool)
PY
)
}

is_completed_tool() {
  array_contains "$1" "${COMPLETED_TOOLS[@]}"
}

should_prompt_codex() {
  local explicitly_selected=0
  local item
  for item in "${SELECTED_TOOLS[@]}"; do
    if [[ "$item" == "codex" ]]; then
      explicitly_selected=1
      break
    fi
  done
  if [[ $explicitly_selected -eq 1 ]]; then
    return 1
  fi
  if [[ ! -t 0 ]]; then
    return 1
  fi
  local reply
  read -r -p "Install codex tool for this run? [y/N]: " reply
  if [[ "${reply,,}" == "y" || "${reply,,}" == "yes" ]]; then
    return 1
  fi
  return 0
}

execute_tools() {
  local tool
  for tool in "${FINAL_TOOLS[@]}"; do
    if [[ "$tool" == "codex" ]] && should_prompt_codex; then
      echo "Skipping codex by user choice."
      continue
    fi

    if is_completed_tool "$tool"; then
      echo "[resume] Skipping already completed tool: $tool"
      continue
    fi

    local script="$SCRIPTS_DIR/${tool}.sh"
    local version
    version=$(get_version "$tool")

    if [[ $DRY_RUN -eq 1 ]]; then
      echo "[dry-run] Would run tool: $tool (script=$script version='${version}')"
      continue
    fi

    echo "==> Running tool: $tool"
    export VM_TOOL_NAME="$tool"
    export VM_TOOL_VERSION="$version"
    if bash "$script"; then
      COMPLETED_TOOLS+=("$tool")
      state_write ""
    else
      echo "Tool failed: $tool" >&2
      state_write "$tool"
      exit 1
    fi
  done
}

main() {
  parse_args "$@"

  if [[ $LIST_PROFILES -eq 1 ]]; then
    list_profiles
    exit 0
  fi
  if [[ $LIST_TOOLS -eq 1 ]]; then
    list_tools
    exit 0
  fi

  if [[ -z "$PROFILE" ]]; then
    echo "--profile is required unless listing." >&2
    show_usage
    exit 1
  fi

  mkdir -p "$STATE_DIR"
  STATE_FILE="$STATE_DIR/${PROFILE}.json"
  STARTED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)

  acquire_lock
  setup_logging

  echo "Profile: $PROFILE"
  echo "Dry run: $DRY_RUN"
  echo "Resume: $RESUME"

  load_profile_payload
  parse_only_tools

  check_os_preflight
  check_binaries_preflight
  check_env_preflight

  resolve_final_tools

  if [[ $RESUME -ne 1 ]]; then
    COMPLETED_TOOLS=()
    state_write ""
    state_set_versions
  else
    state_load_resume
    state_set_versions
  fi

  echo "Resolved profile: $PROFILE_NAME"
  if [[ -n "$PROFILE_DESCRIPTION" ]]; then
    echo "Description: $PROFILE_DESCRIPTION"
  fi
  echo "Planned tool order: ${FINAL_TOOLS[*]}"
  echo "Log file: $LOG_FILE"
  echo "State file: $STATE_FILE"

  execute_tools

  if [[ $DRY_RUN -eq 1 ]]; then
    echo "Dry run complete."
  else
    echo "Installation run complete."
  fi
}

main "$@"
