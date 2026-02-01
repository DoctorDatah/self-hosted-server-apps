#!/usr/bin/env bash
# Automates Cloudflare Tunnel setup for the n8n app + SSH combo.
# Prompts for domains/ports, creates the tunnel, writes config, installs the service.

set -euo pipefail

DEFAULT_TUNNEL_NAME="n8n_vm_app_tunnel"
DEFAULT_APP_DOMAIN="n8napp.arshware.com"
DEFAULT_SSH_DOMAIN="ssh.arshware.com"
DEFAULT_APP_PORT="5678"
CONFIG_PATH="/etc/cloudflared/config.yml"

log() {
  printf '[+] %s\n' "$*"
}

warn() {
  printf '[!] %s\n' "$*" >&2
}

prompt_with_default() {
  local prompt_text="$1"
  local default_value="$2"
  local user_input

  read -r -p "$prompt_text [$default_value]: " user_input
  if [[ -z "$user_input" ]]; then
    echo "$default_value"
  else
    echo "$user_input"
  fi
}

require_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    warn "Missing required command: $cmd"
    return 1
  fi
}

maybe_sudo() {
  if [[ $EUID -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

ensure_cloudflared() {
  if require_cmd cloudflared; then
    return
  fi

  log "Installing cloudflared (requires sudo)..."
  maybe_sudo apt-get update -y
  maybe_sudo apt-get install -y cloudflared

  require_cmd cloudflared
}

ensure_logged_in() {
  if ls "$HOME"/.cloudflared/*.json >/dev/null 2>&1; then
    log "Cloudflare login already detected."
    return
  fi

  log "Running 'cloudflared tunnel login' (browser auth required)..."
  cloudflared tunnel login
}

create_tunnel_if_needed() {
  local tunnel_name="$1"
  if cloudflared tunnel list 2>/dev/null | awk 'NR>1 {print $1}' | grep -Fx "$tunnel_name" >/dev/null; then
    log "Tunnel '$tunnel_name' already exists."
    return
  fi

  log "Creating tunnel '$tunnel_name'..."
  cloudflared tunnel create "$tunnel_name"
}

route_dns() {
  local tunnel_name="$1"
  local hostname="$2"

  if ! cloudflared tunnel route dns "$tunnel_name" "$hostname"; then
    warn "Routing $hostname may already exist. Verify in Cloudflare dashboard."
  fi
}

discover_credentials() {
  local tunnel_name="$1"
  local tunnel_id

  tunnel_id=$(cloudflared tunnel info "$tunnel_name" 2>/dev/null | awk '/Tunnel ID/ {print $3}')
  if [[ -n "$tunnel_id" && -f "$HOME/.cloudflared/${tunnel_id}.json" ]]; then
    echo "$HOME/.cloudflared/${tunnel_id}.json"
    return
  fi

  local first_json
  first_json=$(ls "$HOME"/.cloudflared/*.json 2>/dev/null | head -n1 || true)
  if [[ -n "$first_json" ]]; then
    echo "$first_json"
    return
  fi

  echo ""
}

deploy_credentials() {
  local creds_src="$1"
  local creds_filename

  creds_filename="$(basename "$creds_src")"
  maybe_sudo mkdir -p /etc/cloudflared
  maybe_sudo cp "$creds_src" "/etc/cloudflared/$creds_filename"
  maybe_sudo chmod 600 "/etc/cloudflared/$creds_filename"
  maybe_sudo chown root:root "/etc/cloudflared/$creds_filename"

  echo "/etc/cloudflared/$creds_filename"
}

write_config() {
  local tunnel_name="$1"
  local ssh_domain="$2"
  local app_domain="$3"
  local app_port="$4"
  local creds_path="$5"

  log "Writing $CONFIG_PATH ..."
  cat <<EOF | maybe_sudo tee "$CONFIG_PATH" >/dev/null
tunnel: $tunnel_name
credentials-file: $creds_path

ingress:
  - hostname: $ssh_domain
    service: tcp://localhost:22
  - hostname: $app_domain
    service: http://localhost:$app_port
  - service: http_status:404
EOF
}

install_service() {
  log "Installing and starting cloudflared systemd service..."
  maybe_sudo cloudflared service install
  maybe_sudo systemctl enable cloudflared
  maybe_sudo systemctl restart cloudflared
  maybe_sudo systemctl status cloudflared --no-pager
}

verify_local_app() {
  local app_port="$1"
  if ! curl -I --max-time 5 "http://localhost:${app_port}" >/dev/null 2>&1; then
    warn "Could not reach http://localhost:${app_port}. Ensure n8n is running locally."
  else
    log "Local app responded on port ${app_port}."
  fi
}

main() {
  log "Cloudflare Tunnel (n8n + SSH) setup"

  local tunnel_name ssh_domain app_domain app_port
  tunnel_name=$(prompt_with_default "Tunnel name" "$DEFAULT_TUNNEL_NAME")
  app_domain=$(prompt_with_default "App domain (points to n8n)" "$DEFAULT_APP_DOMAIN")
  ssh_domain=$(prompt_with_default "SSH domain" "$DEFAULT_SSH_DOMAIN")
  app_port=$(prompt_with_default "Local app port" "$DEFAULT_APP_PORT")

  echo
  log "Summary"
  printf '  Tunnel: %s\n  SSH domain: %s\n  App domain: %s\n  Local app port: %s\n\n' \
    "$tunnel_name" "$ssh_domain" "$app_domain" "$app_port"

  read -r -p "Proceed with these settings? [y/N]: " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    warn "Aborted by user."
    exit 1
  fi

  ensure_cloudflared
  ensure_logged_in
  create_tunnel_if_needed "$tunnel_name"
  route_dns "$tunnel_name" "$app_domain"
  route_dns "$tunnel_name" "$ssh_domain"

  local creds_src creds_path
  creds_src=$(discover_credentials "$tunnel_name")
  if [[ -z "$creds_src" ]]; then
    warn "Could not find tunnel credentials in ~/.cloudflared/"
    exit 1
  fi

  creds_path=$(deploy_credentials "$creds_src")
  write_config "$tunnel_name" "$ssh_domain" "$app_domain" "$app_port" "$creds_path"
  install_service
  verify_local_app "$app_port"

  cat <<EOF

Done. Next steps:
- Cloudflare records should now point to this tunnel. Confirm in the dashboard if needed.
- On your Mac, add this to ~/.ssh/config (auto-uses cloudflared path):

Host $ssh_domain
  User malik
  IdentityFile ~/.ssh/id_rsa
  ProxyCommand \$(which cloudflared) access ssh --hostname %h

Then connect with: ssh malik@$ssh_domain
EOF
}

main "$@"
