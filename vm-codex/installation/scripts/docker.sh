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

# shellcheck disable=SC1091
source /etc/os-release
DISTRO_ID="${ID:-ubuntu}"
CODENAME="${VERSION_CODENAME:-}"
if [[ -z "$CODENAME" ]]; then
  CODENAME=$(lsb_release -cs 2>/dev/null || true)
fi
if [[ -z "$CODENAME" ]]; then
  echo "ERROR: Could not detect distro codename for Docker repo." >&2
  exit 1
fi

run_root apt-get update
run_root apt-get install -y ca-certificates curl gnupg
run_root install -m 0755 -d /etc/apt/keyrings
run_root curl -fsSL "https://download.docker.com/linux/${DISTRO_ID}/gpg" | run_root gpg --dearmor -o /etc/apt/keyrings/docker.gpg
run_root chmod a+r /etc/apt/keyrings/docker.gpg
run_root bash -c "echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${DISTRO_ID} ${CODENAME} stable' > /etc/apt/sources.list.d/docker.list"
run_root apt-get update
run_root apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

echo "Docker installed."

DEFAULT_DOCKER_USER="${SUDO_USER:-${USER:-}}"
if [[ -z "${DEFAULT_DOCKER_USER// }" ]]; then
  DEFAULT_DOCKER_USER="$(id -un)"
fi
DOCKER_USER="$DEFAULT_DOCKER_USER"
if [[ -t 0 ]]; then
  read -r -p "Add user to docker group [Default: ${DEFAULT_DOCKER_USER}]: " user_input
  if [[ -n "${user_input// }" ]]; then
    DOCKER_USER="$user_input"
  fi
fi

if id "$DOCKER_USER" >/dev/null 2>&1; then
  echo "Adding user '${DOCKER_USER}' to docker group..."
  run_root usermod -aG docker "$DOCKER_USER" || true
  echo "Note: log out and back in (or reboot) for group changes to apply."
else
  echo "User '${DOCKER_USER}' not found; skipping docker group update."
fi
