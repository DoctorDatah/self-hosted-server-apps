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

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  echo "Docker and Compose already installed."
  exit 0
fi

require_root_or_sudo

run_root apt-get update
run_root apt-get install -y ca-certificates curl gnupg
run_root install -m 0755 -d /etc/apt/keyrings
run_root curl -fsSL https://download.docker.com/linux/ubuntu/gpg | run_root gpg --dearmor -o /etc/apt/keyrings/docker.gpg
run_root chmod a+r /etc/apt/keyrings/docker.gpg
run_root bash -c 'echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" > /etc/apt/sources.list.d/docker.list'
run_root apt-get update
run_root apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Docker installed."
