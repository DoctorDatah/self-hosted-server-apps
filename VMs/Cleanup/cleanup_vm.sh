#!/usr/bin/env bash
set -euo pipefail

# Comprehensive VM cleanup with full or selective mode.

FULL_CLEAN=false

confirm() {
  local prompt="$1"
  local reply
  read -r -p "${prompt} [y/N]: " reply
  [[ "${reply,,}" == "y" || "${reply,,}" == "yes" ]]
}

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

echo "VM Cleanup Script"
echo "This can remove containers, volumes, images, networks, repos, data dirs, and uninstall packages."
echo

if confirm "Full clean (no further prompts; removes everything listed)?"; then
  FULL_CLEAN=true
fi

do_step() {
  local prompt="$1"
  if [[ "$FULL_CLEAN" == "true" ]]; then
    return 0
  fi
  confirm "$prompt"
}

require_root_or_sudo

# --- Docker containers/volumes/images/networks ---
if command -v docker >/dev/null 2>&1; then
  if do_step "Stop and remove all Docker containers?"; then
    while IFS= read -r cid; do
      [[ -z "$cid" ]] && continue
      run_root docker rm -f "$cid"
    done < <(run_root docker ps -aq)
  fi

  if do_step "Remove all Docker volumes?"; then
    while IFS= read -r vid; do
      [[ -z "$vid" ]] && continue
      run_root docker volume rm -f "$vid"
    done < <(run_root docker volume ls -q)
  fi

  if do_step "Remove all Docker images?"; then
    while IFS= read -r iid; do
      [[ -z "$iid" ]] && continue
      run_root docker image rm -f "$iid"
    done < <(run_root docker image ls -q)
  fi

  if do_step "Remove all Docker networks (except default)?"; then
    while IFS= read -r nname; do
      [[ -z "$nname" ]] && continue
      run_root docker network rm "$nname"
    done < <(run_root docker network ls --format '{{.Name}}' | grep -v -E '^(bridge|host|none)$')
  fi
else
  echo "Docker not found; skipping container cleanup."
fi

# --- App data directories ---
if do_step "Remove app data directories (e.g., /data/coolify)?"; then
  run_root rm -rf /data/coolify
fi

# --- Repo cleanup ---
if do_step "Remove repo folders (/home/malik/self-hosted-server-apps and /root/self-hosted-server-apps)?"; then
  run_root rm -rf /home/malik/self-hosted-server-apps
  run_root rm -rf /root/self-hosted-server-apps
fi

# --- Uninstall packages ---
if do_step "Uninstall Docker Engine + Compose plugin?"; then
  run_root apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin || true
  run_root rm -rf /var/lib/docker /var/lib/containerd
fi

if do_step "Uninstall Git?"; then
  run_root apt-get purge -y git || true
fi

if do_step "Uninstall Python3 + pip?"; then
  run_root apt-get purge -y python3 python3-pip || true
fi

if do_step "Run apt autoremove to clean unused packages?"; then
  run_root apt-get autoremove -y || true
fi

echo "Cleanup complete."
