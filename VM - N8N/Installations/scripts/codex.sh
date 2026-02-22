#!/usr/bin/env bash
set -euo pipefail

# Installs OpenAI Codex CLI on Debian/Ubuntu via npm.

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
REQUIREMENTS_FILE="$SCRIPT_DIR/../requirements.txt"

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

if command -v codex >/dev/null 2>&1; then
  echo "Codex CLI already installed."
  exit 0
fi

require_root_or_sudo

if ! command -v npm >/dev/null 2>&1; then
  run_root apt-get update
  run_root apt-get install -y nodejs npm
fi

CODEX_VERSION=""
if [[ -f "$REQUIREMENTS_FILE" ]]; then
  CODEX_VERSION=$(grep -E '^CODEX_CLI_VERSION=' "$REQUIREMENTS_FILE" | tail -n 1 | cut -d= -f2-)
fi

if [[ -n "${CODEX_VERSION// }" ]]; then
  echo "Installing Codex CLI @ ${CODEX_VERSION}..."
  run_root npm install -g "@openai/codex@${CODEX_VERSION}"
else
  echo "Installing Codex CLI (latest)..."
  run_root npm install -g @openai/codex
fi

echo "Codex CLI installed."
