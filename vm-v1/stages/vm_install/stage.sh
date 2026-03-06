#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# shellcheck disable=SC1091
source "$SCRIPT_DIR/../_common/params.sh"

INSTALL_DOCKER="$(vmcx_param_bool install_docker true)"
INSTALL_GIT="$(vmcx_param_bool install_git true)"
INSTALL_UTILS="$(vmcx_param_bool install_utils true)"
INSTALL_PYTHON="$(vmcx_param_bool install_python true)"
INSTALL_INFISICAL="$(vmcx_param_bool install_infisical false)"
INSTALL_CODEX="$(vmcx_param_bool install_codex false)"
CREATE_NETWORK="$(vmcx_param_bool create_network true)"
NETWORK_NAME="$(vmcx_param_get network_name appnet)"

require_root_or_sudo() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    return 0
  fi
  echo "ERROR: This script requires root or sudo." >&2
  exit 1
}

run_root() {
  if [[ ${EUID:-$(id -u)} -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

if ! vmcx_is_linux; then
  echo "[vm_install] non-linux host detected, skipping apt-based installation"
  exit 0
fi

if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  source /etc/os-release
  if [[ "${ID:-}" != "ubuntu" && "${ID_LIKE:-}" != *debian* ]]; then
    echo "[vm_install] unsupported distro for legacy installer: ${ID:-unknown}; skipping"
    exit 0
  fi
fi

echo "[vm_install] target=${VMCX_TARGET_ID:-unknown} mode=${VMCX_EXEC_MODE:-unknown}"
require_root_or_sudo

if [[ "$INSTALL_UTILS" == "true" ]]; then
  if command -v curl >/dev/null 2>&1 && command -v wget >/dev/null 2>&1; then
    echo "[vm_install] curl and wget already installed"
  else
    echo "[vm_install] installing curl + wget"
    run_root apt-get update
    run_root apt-get install -y curl wget ca-certificates gnupg
  fi
fi

if [[ "$INSTALL_GIT" == "true" ]]; then
  if command -v git >/dev/null 2>&1; then
    echo "[vm_install] git already installed"
  else
    echo "[vm_install] installing git"
    run_root apt-get update
    run_root apt-get install -y git
  fi
fi

if [[ "$INSTALL_PYTHON" == "true" ]]; then
  if command -v python3 >/dev/null 2>&1; then
    echo "[vm_install] python3 already installed"
  else
    echo "[vm_install] installing python3 + pip"
    run_root apt-get update
    run_root apt-get install -y python3 python3-pip
  fi
fi

if [[ "$INSTALL_DOCKER" == "true" ]]; then
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    echo "[vm_install] docker + compose already installed"
  else
    echo "[vm_install] installing docker (legacy script flow)"
    run_root apt-get update
    run_root apt-get install -y ca-certificates curl gnupg
    run_root install -m 0755 -d /etc/apt/keyrings
    if [[ ! -f /etc/apt/keyrings/docker.gpg ]]; then
      curl -fsSL "https://download.docker.com/linux/${ID:-ubuntu}/gpg" | run_root gpg --dearmor -o /etc/apt/keyrings/docker.gpg
      run_root chmod a+r /etc/apt/keyrings/docker.gpg
    fi

    CODENAME="${VERSION_CODENAME:-}"
    if [[ -z "$CODENAME" ]]; then
      CODENAME=$(lsb_release -cs 2>/dev/null || true)
    fi
    if [[ -z "$CODENAME" ]]; then
      echo "ERROR: could not detect distro codename for Docker repo" >&2
      exit 1
    fi

    run_root bash -c "echo 'deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/${ID:-ubuntu} ${CODENAME} stable' > /etc/apt/sources.list.d/docker.list"
    run_root apt-get update
    run_root apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    echo "[vm_install] docker installed"
  fi

  DEFAULT_DOCKER_USER="${SUDO_USER:-${USER:-}}"
  if [[ -n "${DEFAULT_DOCKER_USER// }" ]] && id "$DEFAULT_DOCKER_USER" >/dev/null 2>&1; then
    run_root usermod -aG docker "$DEFAULT_DOCKER_USER" || true
    echo "[vm_install] added ${DEFAULT_DOCKER_USER} to docker group"
  fi
fi

if [[ "$CREATE_NETWORK" == "true" ]]; then
  if ! command -v docker >/dev/null 2>&1; then
    echo "[vm_install] docker missing; skipping network creation"
  elif docker network inspect "$NETWORK_NAME" >/dev/null 2>&1; then
    echo "[vm_install] docker network exists: $NETWORK_NAME"
  else
    echo "[vm_install] creating docker network: $NETWORK_NAME"
    run_root docker network create "$NETWORK_NAME" >/dev/null
  fi
fi

if [[ "$INSTALL_INFISICAL" == "true" ]]; then
  if command -v infisical >/dev/null 2>&1; then
    echo "[vm_install] infisical already installed"
  else
    echo "[vm_install] installing infisical CLI"
    run_root bash -c "curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | bash"
    run_root apt-get update
    run_root apt-get install -y infisical
  fi
fi

if [[ "$INSTALL_CODEX" == "true" ]]; then
  if command -v codex >/dev/null 2>&1; then
    echo "[vm_install] codex already installed"
  else
    if ! command -v npm >/dev/null 2>&1; then
      run_root apt-get update
      run_root apt-get install -y nodejs npm
    fi
    run_root npm install -g @openai/codex
    echo "[vm_install] codex installed"
  fi
fi

echo "[vm_install] complete"
