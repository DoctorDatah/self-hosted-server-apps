#!/usr/bin/env bash
set -euo pipefail

# Coolify deployer wrapper
# - Runs Coolify's official installer with a few guardrails for your VM.
# - Lets you preseed Docker network pool/registry and optionally the initial Coolify root user.
# - Run as root inside the Coolify VM (not on the Proxmox host).

INSTALLER_URL="https://cdn.coollabs.io/coolify/install.sh"
DEFAULT_POOL_BASE="10.0.0.0/8"
DEFAULT_POOL_SIZE="24"
DEFAULT_REGISTRY="ghcr.io"

auto_approve=false
requested_version="${COOLIFY_VERSION:-}"
pool_base="${COOLIFY_POOL_BASE:-$DEFAULT_POOL_BASE}"
pool_size="${COOLIFY_POOL_SIZE:-$DEFAULT_POOL_SIZE}"
registry_url="${COOLIFY_REGISTRY:-$DEFAULT_REGISTRY}"
autoupdate="${COOLIFY_AUTOUPDATE:-true}"
force_pool_override="${COOLIFY_FORCE_POOL_OVERRIDE:-false}"

root_username="${COOLIFY_ROOT_USERNAME:-}"
root_email="${COOLIFY_ROOT_EMAIL:-}"
root_password="${COOLIFY_ROOT_PASSWORD:-}"

usage() {
  cat <<'EOF'
Usage: ./coolify-deployer.sh [options]

Options:
  -y, --yes                 Skip confirmation prompt
  --version <v>             Pin Coolify version (blank/omit = latest from Coolify CDN)
  --registry <url>          Registry for Coolify images (default: ghcr.io)
  --pool-base <cidr>        Docker default address pool base (default: 10.0.0.0/8)
  --pool-size <size>        Docker default address pool size (default: 24)
  --force-pool-override     Force override Docker pool even if already set
  --autoupdate <true|false> Enable/disable Coolify auto-updates (default: true)
  -h, --help                Show this help

Environment overrides:
  COOLIFY_ROOT_USERNAME / COOLIFY_ROOT_EMAIL / COOLIFY_ROOT_PASSWORD
  COOLIFY_VERSION / COOLIFY_REGISTRY / COOLIFY_POOL_BASE / COOLIFY_POOL_SIZE
  COOLIFY_AUTOUPDATE / COOLIFY_FORCE_POOL_OVERRIDE
EOF
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: $1 is required. Install it and rerun." >&2
    exit 1
  }
}

confirm() {
  local prompt="$1"
  read -rp "$prompt (y/N): " ans
  [[ ${ans,,} == "y" ]]
}

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: Run as root inside the target VM (sudo -i)." >&2
  exit 1
fi

require_cmd curl

while [[ $# -gt 0 ]]; do
  case "$1" in
    -y|--yes)
      auto_approve=true
      ;;
    --version)
      [[ $# -lt 2 ]] && { echo "Missing value for --version" >&2; exit 1; }
      requested_version="$2"
      shift
      ;;
    --registry)
      [[ $# -lt 2 ]] && { echo "Missing value for --registry" >&2; exit 1; }
      registry_url="$2"
      shift
      ;;
    --pool-base)
      [[ $# -lt 2 ]] && { echo "Missing value for --pool-base" >&2; exit 1; }
      pool_base="$2"
      shift
      ;;
    --pool-size)
      [[ $# -lt 2 ]] && { echo "Missing value for --pool-size" >&2; exit 1; }
      pool_size="$2"
      shift
      ;;
    --force-pool-override)
      force_pool_override=true
      ;;
    --autoupdate)
      [[ $# -lt 2 ]] && { echo "Missing value for --autoupdate" >&2; exit 1; }
      autoupdate="${2,,}"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      exit 1
      ;;
  esac
  shift
done

autoupdate="${autoupdate,,}"
if [[ "$autoupdate" != "true" && "$autoupdate" != "false" ]]; then
  echo "Invalid value for --autoupdate: $autoupdate (use true or false)" >&2
  exit 1
fi

force_pool_override="${force_pool_override,,}"
if [[ "$force_pool_override" != "true" && "$force_pool_override" != "false" ]]; then
  force_pool_override="false"
fi

[[ -z "$pool_base" ]] && pool_base="$DEFAULT_POOL_BASE"
[[ -z "$pool_size" ]] && pool_size="$DEFAULT_POOL_SIZE"
[[ -z "$registry_url" ]] && registry_url="$DEFAULT_REGISTRY"

if [[ -d /etc/pve && $auto_approve == false ]]; then
  echo "Detected /etc/pve; this looks like a Proxmox host."
  confirm "You probably want to run this inside the vm-coolify guest. Continue anyway?" || exit 1
fi

mem_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo 2>/dev/null || echo 0)
disk_gb=$(df -BG / | awk 'NR==2 {gsub("G","",$4); print $4}' 2>/dev/null || echo 0)

if (( mem_mb > 0 && mem_mb < 2048 )); then
  echo "WARNING: Only ${mem_mb}MB RAM detected. Coolify recommends at least 2GB."
fi
if (( disk_gb > 0 && disk_gb < 20 )); then
  echo "WARNING: Only ${disk_gb}GB free on /. Coolify install wants ~20GB free."
fi

if [[ -z "$requested_version" && $auto_approve == false ]]; then
  read -rp "Coolify version to install [latest]: " input
  requested_version="${input:-}"
fi

if [[ $auto_approve == false ]]; then
  read -rp "Docker address pool base [$pool_base]: " input
  pool_base="${input:-$pool_base}"

  read -rp "Docker address pool size [$pool_size]: " input
  pool_size="${input:-$pool_size}"

  read -rp "Registry URL [$registry_url]: " input
  registry_url="${input:-$registry_url}"

  read -rp "Disable Coolify auto-updates? (y/N): " input
  [[ ${input,,} == "y" ]] && autoupdate="false" || autoupdate="true"

  read -rp "Force override Docker pool if already set? (y/N): " input
  [[ ${input,,} == "y" ]] && force_pool_override=true

  if [[ -z "$root_username" ]]; then
    read -rp "Seed Coolify root username (blank to skip): " root_username
  fi
  if [[ -n "$root_username" && -z "$root_email" ]]; then
    read -rp "Root email: " root_email
  fi
  if [[ -n "$root_username" && -z "$root_password" ]]; then
    read -rsp "Root password (will not echo): " root_password
    echo
  fi
fi

if [[ -n "$root_username" || -n "$root_email" || -n "$root_password" ]]; then
  if [[ -z "$root_username" || -z "$root_email" || -z "$root_password" ]]; then
    echo "ERROR: To preseed the Coolify root user you must provide username, email, and password." >&2
    exit 1
  fi
fi

version_label="${requested_version:-latest (auto from Coolify)}"
echo
echo "Coolify deploy settings:"
echo "  Version          : $version_label"
echo "  Registry         : $registry_url"
echo "  Docker pool      : $pool_base (size $pool_size) override=${force_pool_override}"
echo "  Auto-updates     : $autoupdate"
if [[ -n "$root_username" ]]; then
  echo "  Seed root user   : yes ($root_username / $root_email)"
else
  echo "  Seed root user   : no (create via UI after install)"
fi
echo

if [[ $auto_approve == false ]]; then
  confirm "Proceed with Coolify installation using the official installer?" || exit 0
fi

tmp_script="$(mktemp /tmp/coolify-install-XXXXXX.sh)"
cleanup() { rm -f "$tmp_script"; }
trap cleanup EXIT

echo "Downloading installer from $INSTALLER_URL ..."
if ! curl -fsSL "$INSTALLER_URL" -o "$tmp_script"; then
  echo "ERROR: Failed to download $INSTALLER_URL" >&2
  exit 1
fi
chmod +x "$tmp_script"

INSTALL_ENV=(
  REGISTRY_URL="$registry_url"
  DOCKER_ADDRESS_POOL_BASE="$pool_base"
  DOCKER_ADDRESS_POOL_SIZE="$pool_size"
)

[[ "$autoupdate" == "false" ]] && INSTALL_ENV+=(AUTOUPDATE="false")
[[ "$force_pool_override" == "true" ]] && INSTALL_ENV+=(DOCKER_POOL_FORCE_OVERRIDE="true")

if [[ -n "$root_username" ]]; then
  INSTALL_ENV+=(
    ROOT_USERNAME="$root_username"
    ROOT_USER_EMAIL="$root_email"
    ROOT_USER_PASSWORD="$root_password"
  )
fi

VERSION_ARGS=()
[[ -n "$requested_version" ]] && VERSION_ARGS+=("$requested_version")

echo "Running Coolify installer (this may take several minutes)..."
env "${INSTALL_ENV[@]}" bash "$tmp_script" "${VERSION_ARGS[@]}"
echo "Coolify installer finished. If you see errors above, check /data/coolify/source/installation-*.log."
