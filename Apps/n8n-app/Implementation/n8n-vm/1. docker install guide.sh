#!/usr/bin/env bash
set -euo pipefail

# Installs Docker Engine + Compose plugin on the VM using pinned versions.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REPO_ROOT=$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null || true)

if [[ -z "$REPO_ROOT" ]]; then
  echo "ERROR: Could not determine repo root. Run this script from within the repo." >&2
  exit 1
fi

PACKAGES_FILE="$REPO_ROOT/Apps/n8n-app/ops/system-packages.txt"

if [[ ! -f "$PACKAGES_FILE" ]]; then
  echo "ERROR: Missing package list at $PACKAGES_FILE" >&2
  exit 1
fi

if ! command -v lsb_release >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y lsb-release
fi

codename=$(lsb_release -cs)
if [[ "$codename" != "noble" ]]; then
  echo "ERROR: This script targets Ubuntu 24.04 (noble). Detected: $codename" >&2
  exit 1
fi

sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg

sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $codename stable" | \
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
