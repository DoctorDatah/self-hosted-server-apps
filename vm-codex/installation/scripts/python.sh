#!/usr/bin/env bash
set -euo pipefail

require_root_or_sudo() {
  if [[ $EUID -eq 0 ]]; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    return 0
  fi
  echo "ERROR: This script requires root or sudo." >&2
  exit 1
}

run_root() {
  if [[ $EUID -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

if command -v python3 >/dev/null 2>&1; then
  echo "Python3 already installed."
  exit 0
fi

require_root_or_sudo

run_root apt-get update
run_root apt-get install -y python3 python3-pip

echo "Python3 installed."
