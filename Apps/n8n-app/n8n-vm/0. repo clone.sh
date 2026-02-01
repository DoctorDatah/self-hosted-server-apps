#!/usr/bin/env bash
set -euo pipefail

# Clones the repo onto the VM for subsequent install scripts.

REPO_URL="https://github.com/DoctorDatah/self-hosted-server-apps"
REPO_DIR="${REPO_DIR:-$HOME/self-hosted-server-apps}"

if ! command -v git >/dev/null 2>&1; then
  echo "Git not found. Installing..." >&2
  sudo apt-get update
  sudo apt-get install -y git
fi

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "Repo already exists at $REPO_DIR"
  exit 0
fi

git clone "$REPO_URL" "$REPO_DIR"
echo "Repo cloned to: $REPO_DIR"
