#!/usr/bin/env bash
set -euo pipefail

# Cloudflare Tunnel setup for Coolify (UI + WebSockets)
# - Installs cloudflared
# - Creates a config file for a named tunnel
# - Suggests routes for Coolify UI and WebSockets

SUDO=""
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
  else
    echo "This script needs root access for install/config, but sudo was not found."
    exit 1
  fi
fi

read -r -p "Tunnel name (default: coolify-tunnel): " TUNNEL_NAME
read -r -p "Domain (default: coolify.arshware.com): " DOMAIN
read -r -p "Local Coolify URL (default: http://127.0.0.1:8000): " LOCAL_URL

if [[ -z "${TUNNEL_NAME}" ]]; then
  TUNNEL_NAME="coolify-tunnel"
fi

if [[ -z "${DOMAIN}" ]]; then
  DOMAIN="coolify.arshware.com"
fi

if [[ -z "${LOCAL_URL}" ]]; then
  LOCAL_URL="http://127.0.0.1:8000"
fi

if [[ -z "${TUNNEL_NAME}" || -z "${DOMAIN}" || -z "${LOCAL_URL}" ]]; then
  echo "Tunnel name, domain, and local URL are required."
  exit 1
fi

install_cloudflared() {
  echo "Installing cloudflared..."
  ${SUDO} apt-get update -y
  if ${SUDO} apt-get install -y cloudflared; then
    return 0
  fi

  echo "cloudflared not found in default repos. Adding Cloudflare repo..."
  ${SUDO} apt-get install -y ca-certificates curl gnupg
  ${SUDO} install -m 0755 -d /usr/share/keyrings
  curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | ${SUDO} gpg --dearmor -o /usr/share/keyrings/cloudflare-main.gpg
  DISTRO_CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME}")"
  echo "deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared ${DISTRO_CODENAME} main" | ${SUDO} tee /etc/apt/sources.list.d/cloudflared.list >/dev/null
  ${SUDO} apt-get update -y
  ${SUDO} apt-get install -y cloudflared
}

# Install cloudflared if missing
if ! command -v cloudflared >/dev/null 2>&1; then
  install_cloudflared
fi

CONFIG_DIR="/etc/cloudflared"
CONFIG_FILE="${CONFIG_DIR}/config.yml"

${SUDO} mkdir -p "${CONFIG_DIR}"

${SUDO} tee "${CONFIG_FILE}" > /dev/null <<CFG
# Cloudflare Tunnel config for Coolify
# You still need to:
# 1) Create the tunnel in Cloudflare Zero Trust
# 2) Download credentials and place them at /etc/cloudflared/<tunnel-id>.json
# 3) Add DNS route for ${DOMAIN}

# Example:
# cloudflared tunnel login
# cloudflared tunnel create ${TUNNEL_NAME}
# cloudflared tunnel route dns ${TUNNEL_NAME} ${DOMAIN}

# Then update the 'credentials-file' below with the real tunnel ID.

# tunnel: <tunnel-id>
# credentials-file: /etc/cloudflared/<tunnel-id>.json

ingress:
  # Main Coolify UI
  - hostname: ${DOMAIN}
    service: ${LOCAL_URL}

  # Terminal WebSocket (Coolify)
  - hostname: ${DOMAIN}
    path: /terminal/ws
    service: ${LOCAL_URL}

  # Realtime WebSocket (Coolify /app/*)
  - hostname: ${DOMAIN}
    path: /app
    service: ${LOCAL_URL}

  # Fallback
  - service: http_status:404
CFG

${SUDO} chmod 600 "${CONFIG_FILE}"

echo
"Config written to ${CONFIG_FILE}"
cat <<'NEXT'

Next steps (run on the server):
1) Login to Cloudflare:
   cloudflared tunnel login

2) Create the tunnel:
   cloudflared tunnel create <tunnel-name>

3) Add DNS route:
   cloudflared tunnel route dns <tunnel-name> <domain>

4) Update /etc/cloudflared/config.yml with the real tunnel ID + credentials path.

5) Run the tunnel as a service:
   cloudflared service install
   systemctl enable --now cloudflared

Then test:
- Open https://<domain>
- Terminal should connect without websocket errors
NEXT
