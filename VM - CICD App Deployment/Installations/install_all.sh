#!/usr/bin/env bash
set -euo pipefail

# Runs all tool scripts in this folder (except itself).

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

show_usage() {
  cat <<'USAGE'
Usage: ./install_all.sh [--only tool1,tool2]

Runs all tool install scripts in this folder (e.g. docker.sh).

Options:
  --only   Comma-separated list of tools to run (e.g. docker,git,python)
USAGE
}

ONLY=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)
      shift
      ONLY="${1-}"
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

run_script() {
  local script="$1"
  echo "==> Running ${script##*/}"
  bash "$script"
}

mapfile -t scripts < <(ls -1 "$SCRIPTS_DIR"/*.sh 2>/dev/null || true)
if [[ ${#scripts[@]} -eq 0 ]]; then
  echo "No install scripts found in $SCRIPT_DIR" >&2
  exit 1
fi

if [[ -n "$ONLY" ]]; then
  IFS=',' read -r -a only_list <<< "$ONLY"
  for tool in "${only_list[@]}"; do
    tool="${tool// /}"
    if [[ -z "$tool" ]]; then
      continue
    fi
    target="${SCRIPTS_DIR}/${tool}.sh"
    if [[ ! -f "$target" ]]; then
      echo "Unknown tool: $tool (expected $target)" >&2
      exit 1
    fi
    run_script "$target"
  done
  exit 0
fi

for script in "${scripts[@]}"; do
  run_script "$script"
done
