#!/usr/bin/env bash
set -euo pipefail

# Installs Infisical CLI on Ubuntu/Debian.

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

require_root_or_sudo

if ! command -v curl >/dev/null 2>&1; then
  run_root apt-get update
  run_root apt-get install -y curl
fi

echo "Installing Infisical CLI..."
curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | run_root bash
run_root apt-get update
run_root apt-get install -y infisical

echo "Infisical CLI installed."
