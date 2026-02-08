#!/usr/bin/env bash
set -euo pipefail

NETWORK_NAME="appnet"

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

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: Docker is missing. Run docker install first." >&2
  exit 1
fi

if docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
  echo "Docker network exists: ${NETWORK_NAME}"
  exit 0
fi

require_root_or_sudo
echo "Creating Docker network: ${NETWORK_NAME}"
run_root docker network create "$NETWORK_NAME" >/dev/null
echo "Docker network created."
