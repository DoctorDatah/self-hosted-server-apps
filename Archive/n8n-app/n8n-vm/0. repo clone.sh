#!/usr/bin/env bash
set -euo pipefail

# Clones the repo or pulls updates if it already exists.

REPO_URL="https://github.com/DoctorDatah/self-hosted-server-apps"
REPO_DIR="${REPO_DIR:-$HOME/self-hosted-server-apps}"

if ! command -v git >/dev/null 2>&1; then
  echo "Git not found. Installing..." >&2
  sudo apt-get update
  sudo apt-get install -y git
fi

if [[ -d "$REPO_DIR/.git" ]]; then
  echo "Repo exists at $REPO_DIR. Pulling latest changes..."
  git -C "$REPO_DIR" pull
  exit 0
fi

git clone "$REPO_URL" "$REPO_DIR"
echo "Repo cloned to: $REPO_DIR"
