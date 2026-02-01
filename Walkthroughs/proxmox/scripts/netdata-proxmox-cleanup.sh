#!/usr/bin/env bash
set -euo pipefail

say(){ echo -e "\n==> $*"; }
ok(){ echo "[OK] $*"; }
warn(){ echo "[WARN] $*"; }
die(){ echo "[ERROR] $*" >&2; exit 1; }

need_root(){
  [[ "${EUID}" -eq 0 ]] || die "Run as root (sudo)."
}

read_default(){
  local __var="$1" __prompt="$2" __default="$3" val
  read -r -p "$__prompt (default: $__default): " val
  val="${val:-$__default}"
  printf -v "$__var" "%s" "$val"
}

ask_yes_no(){
  local __var="$1" __prompt="$2" __default="$3" reply
  local hint
  if [[ "${__default,,}" == "y" ]]; then
    hint="Y/n"
  else
    hint="y/N"
  fi
  read -r -p "$__prompt [$hint]: " reply
  reply="${reply:-$__default}"
  case "${reply,,}" in
    y|yes) printf -v "$__var" "y" ;;
    n|no)  printf -v "$__var" "n" ;;
    *)     die "Please answer y or n." ;;
  esac
}

delete_token(){
  local user="$1" token="$2"
  pveum user token del "$user" "$token" >/dev/null 2>&1 && return 0
  pveum user token delete "$user" "$token" >/dev/null 2>&1 && return 0
  return 1
}

need_root

read_default PVE_USER   "Proxmox monitoring user to clean up (name@realm)" "netdata@pam"
[[ "$PVE_USER" == *@* ]] || die "PVE_USER must look like name@realm (e.g., netdata@pam)."
read_default PVE_ROLE   "Proxmox role to optionally remove" "Netdata-Monitor"
read_default TOKEN_BASE "Token base/prefix to match for deletion" "netdata"

ask_yes_no REMOVE_TOKENS "Delete tokens for $PVE_USER starting with \"$TOKEN_BASE\"?" "y"
ask_yes_no REMOVE_ROLE   "Delete role $PVE_ROLE?" "n"
ask_yes_no REMOVE_USER   "Delete user $PVE_USER? (tokens must be removed first)" "n"
ask_yes_no REMOVE_NETDATA_CFG "Remove Netdata Proxmox config files?" "y"
ask_yes_no STOP_NETDATA  "Stop/disable Netdata service?" "y"
ask_yes_no PURGE_NETDATA "Purge Netdata package and data?" "n"
ask_yes_no REMOVE_NGINX  "Remove Nginx Netdata site + htpasswd?" "y"
ask_yes_no PURGE_NGINX   "Also purge nginx/apache2-utils packages?" "n"

# ---------- Tokens ----------
if [[ "$REMOVE_TOKENS" == "y" ]]; then
  say "Deleting matching Proxmox API tokens"
  TOKENS_JSON="$(pveum user token list "$PVE_USER" --output-format json 2>/dev/null || true)"

  if command -v jq >/dev/null 2>&1 && [[ -n "$TOKENS_JSON" ]]; then
    mapfile -t TOKENS < <(
      echo "$TOKENS_JSON" | jq -r --arg base "$TOKEN_BASE" '
        .data // empty
        | map(.tokenid // .id // .name // empty)
        | map(select(. != ""))
        | map(select(startswith($base + "-") or . == $base))
        | .[]
      '
    )
  else
    warn "jq not available or token list empty; falling back to basic parsing"
    mapfile -t TOKENS < <(
      pveum user token list "$PVE_USER" 2>/dev/null \
        | awk -v base="$TOKEN_BASE" 'NR>1 && $1 ~ "^"base {print $1}'
    )
  fi

  if [[ ${#TOKENS[@]} -eq 0 ]]; then
    warn "No tokens found matching \"$TOKEN_BASE\" for $PVE_USER"
  else
    for t in "${TOKENS[@]}"; do
      if delete_token "$PVE_USER" "$t"; then
        ok "Deleted token: ${PVE_USER}!${t}"
      else
        warn "Failed to delete token ${PVE_USER}!${t}"
      fi
    done
  fi
fi

# ---------- Role ----------
if [[ "$REMOVE_ROLE" == "y" ]]; then
  say "Removing role $PVE_ROLE"
  pveum role del "$PVE_ROLE" >/dev/null 2>&1 || pveum role delete "$PVE_ROLE" >/dev/null 2>&1 || warn "Could not remove role $PVE_ROLE"
fi

# ---------- User ----------
if [[ "$REMOVE_USER" == "y" ]]; then
  say "Removing user $PVE_USER"
  pveum user del "$PVE_USER" >/dev/null 2>&1 || pveum user delete "$PVE_USER" >/dev/null 2>&1 || warn "Could not remove user $PVE_USER (check remaining tokens/ACLs)"
fi

# ---------- Netdata config ----------
if [[ "$REMOVE_NETDATA_CFG" == "y" ]]; then
  say "Removing Netdata Proxmox collector config"
  rm -f /etc/netdata/go.d/proxmox.conf
  rm -f /etc/netdata/netdata.conf.d/plugins.conf
fi

if [[ "$STOP_NETDATA" == "y" ]]; then
  say "Stopping/disabling Netdata service"
  systemctl disable --now netdata >/dev/null 2>&1 || systemctl stop netdata >/dev/null 2>&1 || warn "Could not stop/disable netdata"
fi

if [[ "$PURGE_NETDATA" == "y" ]]; then
  say "Purging Netdata package and data"
  apt-get purge -y netdata || warn "apt purge netdata failed"
  apt-get autoremove -y || true
fi

# ---------- Nginx ----------
if [[ "$REMOVE_NGINX" == "y" ]]; then
  say "Removing Nginx Netdata site and credentials"
  rm -f /etc/nginx/sites-enabled/netdata
  rm -f /etc/nginx/sites-available/netdata
  rm -f /etc/nginx/.htpasswd-netdata

  if command -v nginx >/dev/null 2>&1; then
    if nginx -t; then
      systemctl reload nginx || systemctl restart nginx || warn "Nginx reload failed"
    else
      warn "Nginx config test failed; check /etc/nginx/ before reloading"
    fi
  else
    warn "Nginx not installed; skipping reload"
  fi
fi

if [[ "$PURGE_NGINX" == "y" ]]; then
  say "Purging nginx + apache2-utils packages"
  apt-get purge -y nginx apache2-utils || warn "apt purge nginx/apache2-utils failed"
  apt-get autoremove -y || true
fi

say "Cleanup completed. Review any warnings above."
