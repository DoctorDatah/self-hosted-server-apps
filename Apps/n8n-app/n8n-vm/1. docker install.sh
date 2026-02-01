#!/usr/bin/env bash
set -euo pipefail

# Installs Docker Engine + Compose plugin on the VM using pinned versions.

show_usage() {
  cat <<'USAGE'
Usage: 1. docker install.sh

Requires:
  - Repo cloned on the VM (run 0. repo clone.sh first)
  - Apps/n8n-app/requirements/vm_requirments.txt in the repo
  - Ubuntu 22.04 (jammy) or Debian 12 (bookworm)
USAGE
}

if [[ "${1-}" == "-h" || "${1-}" == "--help" ]]; then
  show_usage
  exit 0
fi

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

PACKAGES_FILE="$REPO_ROOT/Apps/n8n-app/requirements/vm_requirments.txt"

if [[ ! -f "$PACKAGES_FILE" ]]; then
  echo "ERROR: Missing package list at $PACKAGES_FILE" >&2
  exit 1
fi

if ! command -v lsb_release >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y lsb-release
fi

os_id=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
codename=$(lsb_release -cs)
repo_base=""
distro_label=""

case "$os_id" in
  ubuntu)
    if [[ "$codename" != "jammy" ]]; then
      echo "ERROR: This script targets Ubuntu 22.04 (jammy). Detected: $codename" >&2
      exit 1
    fi
    repo_base="https://download.docker.com/linux/ubuntu"
    distro_label="ubuntu.22.04"
    ;;
  debian)
    if [[ "$codename" != "bookworm" ]]; then
      echo "ERROR: This script targets Debian 12 (bookworm). Detected: $codename" >&2
      exit 1
    fi
    repo_base="https://download.docker.com/linux/debian"
    distro_label="debian.12"
    ;;
  *)
    echo "ERROR: Unsupported OS. Use Ubuntu 22.04 or Debian 12." >&2
    exit 1
    ;;
esac

if grep -Eq '^(docker-(ce|ce-cli|buildx-plugin|compose-plugin)|containerd\.io)=' "$PACKAGES_FILE"; then
  if ! grep -q "$distro_label" "$PACKAGES_FILE"; then
    echo "ERROR: Pinned Docker packages in $PACKAGES_FILE do not match $distro_label." >&2
    echo "Update pins before running this script." >&2
    exit 1
  fi
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL "$repo_base/gpg" | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] $repo_base $codename stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update

# Install pinned Docker packages from the repo list.
while IFS= read -r line; do
  pkg=$(echo "$line" | sed -e 's/#.*$//' -e 's/^[[:space:]]*//;s/[[:space:]]*$//')
  if [[ -n "$pkg" ]]; then
    sudo apt-get install -y "$pkg"
  fi
done < "$PACKAGES_FILE"

sudo systemctl enable --now docker

echo "Docker installed. Version info:"
docker --version
docker compose version
