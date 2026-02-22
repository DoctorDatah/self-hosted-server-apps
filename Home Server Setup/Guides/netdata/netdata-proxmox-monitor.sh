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

read_secret(){
  local __var="$1" __prompt="$2" val
  read -r -s -p "$__prompt: " val
  echo
  [[ -n "$val" ]] || die "Value cannot be empty."
  printf -v "$__var" "%s" "$val"
}

need_root

# ---------- Inputs ----------
read_default PVE_USER   "Enter Proxmox monitoring user (format name@realm)" "netdata@pam"
[[ "$PVE_USER" == *@* ]] || die "PVE_USER must look like name@realm (e.g., netdata@pam)."

read_default PVE_ROLE   "Enter Proxmox role name to create/use" "Netdata-Monitor"
read_default TOKEN_BASE "Enter Proxmox token base name (script will make a unique one)" "netdata"
[[ "$TOKEN_BASE" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]] || die "TOKEN_BASE invalid. Use letters/numbers/._- only."

read_default NETDATA_PATH "Netdata URL path behind Nginx" "/netdata"
[[ "$NETDATA_PATH" == /* ]] || die "NETDATA_PATH must start with / (e.g., /netdata)."

read_default HTTP_USER  "Choose Netdata dashboard login username" "admin"
read_secret  HTTP_PASS  "Choose Netdata dashboard login password"

PVE_API_URL="https://127.0.0.1:8006/api2/json"

# ---------- Packages ----------
say "Install required packages"
apt-get update -y
apt-get install -y curl ca-certificates nginx apache2-utils jq

# ---------- Install Netdata ----------
say "Install/Update Netdata"
bash <(curl -sL https://my-netdata.io/kickstart.sh) --dont-wait || true
systemctl enable --now netdata
ok "Netdata service enabled"

# ---------- Secure Netdata (bind localhost) ----------
say "Bind Netdata web server to localhost only (127.0.0.1)"
NETDATA_CONF="/etc/netdata/netdata.conf"
mkdir -p /etc/netdata

if [[ ! -f "$NETDATA_CONF" ]]; then
  cat > "$NETDATA_CONF" <<'EOF'
[web]
    bind to = 127.0.0.1
EOF
else
  awk '
    BEGIN{inweb=0}
    /^\[web\]/{inweb=1; print; next}
    /^\[/{if(inweb==1){inweb=0} print; next}
    {
      if(inweb==1 && $0 ~ /^[[:space:]]*bind to[[:space:]]*=/){next}
      print
    }
  ' "$NETDATA_CONF" > "${NETDATA_CONF}.tmp"

  awk '
    BEGIN{done=0}
    /^\[web\]$/ && done==0 {print; print "    bind to = 127.0.0.1"; done=1; next}
    {print}
  ' "${NETDATA_CONF}.tmp" > "$NETDATA_CONF"
  rm -f "${NETDATA_CONF}.tmp"
fi

systemctl restart netdata
ok "Netdata bound to localhost"

# ---------- Ensure go.d enabled ----------
say "Force-enable go.d plugin"
mkdir -p /etc/netdata/netdata.conf.d
cat > /etc/netdata/netdata.conf.d/plugins.conf <<'EOF'
[plugins]
  go.d = yes
EOF
systemctl restart netdata
ok "go.d enabled"

# ---------- Create Proxmox user/role/ACL/token ----------
say "Create/ensure Proxmox user, role, ACL"
pveum user add "$PVE_USER" 2>/dev/null || true
pveum role add "$PVE_ROLE" -privs "Sys.Audit VM.Audit" 2>/dev/null || true
pveum acl add / -user "$PVE_USER" -role "$PVE_ROLE" 2>/dev/null || true
ok "Proxmox RBAC ensured"

say "Create a fresh Proxmox API token and capture secret (JSON)"
TOKEN_ID="${TOKEN_BASE}-$(date +%Y%m%d%H%M%S)"
TOKEN_JSON="$(pveum user token add "$PVE_USER" "$TOKEN_ID" --output-format json 2>/dev/null || true)"
[[ -n "$TOKEN_JSON" ]] || die "Failed to create token (no output)."

SECRET="$(
  echo "$TOKEN_JSON" | jq -r '
    .secret
    // .value
    // (.data // empty | if type=="object" then (.secret // .value) elif type=="array" then (.[0].secret // .[0].value) else empty end)
    // empty
  '
)"
[[ -n "$SECRET" ]] || die "Token created but secret missing from JSON output. Raw: $TOKEN_JSON"

FULL_ID="$(echo "$TOKEN_JSON" | jq -r '."full-tokenid" // empty')"
[[ -n "$FULL_ID" ]] || FULL_ID="${PVE_USER}!${TOKEN_ID}"
ok "Token created: $FULL_ID"

# ---------- Verify token works (must be HTTP 200) ----------
say "Verify token works against Proxmox API (must be HTTP 200)"
CODE="$(curl -sk -o /dev/null -w "%{http_code}" \
  -H "Authorization: PVEAPIToken=${FULL_ID}=${SECRET}" \
  "${PVE_API_URL}/version" || true)"

echo "HTTP code: $CODE"
[[ "$CODE" == "200" ]] || die "Token auth failed (HTTP $CODE). Fix RBAC/user/realm then re-run."

ok "Token authentication OK"

# ---------- Configure Netdata Proxmox collector ----------
say "Configure Netdata Proxmox collector"
mkdir -p /etc/netdata/go.d
cat > /etc/netdata/go.d/proxmox.conf <<EOF
jobs:
  - name: local
    url: ${PVE_API_URL}
    token_id: "${FULL_ID}"
    token_secret: "${SECRET}"
    insecure_skip_verify: true
EOF

chown -R netdata:netdata /etc/netdata/go.d 2>/dev/null || true
systemctl restart netdata
ok "Netdata Proxmox collector configured"

# ---------- Nginx reverse proxy + basic auth ----------
say "Configure Nginx reverse proxy + Basic Auth"
HTPASS="/etc/nginx/.htpasswd-netdata"
htpasswd -bc "$HTPASS" "$HTTP_USER" "$HTTP_PASS" >/dev/null

NGINX_CONF="/etc/nginx/sites-available/netdata"
cat > "$NGINX_CONF" <<EOF
server {
    listen 80;
    server_name _;

    location = ${NETDATA_PATH} { return 301 ${NETDATA_PATH}/; }

    location ${NETDATA_PATH}/ {
        auth_basic "Netdata";
        auth_basic_user_file ${HTPASS};

        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        proxy_http_version 1.1;
        proxy_set_header Connection "";

        proxy_pass http://127.0.0.1:19999/;
    }
}
EOF

ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/netdata
rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
nginx -t
systemctl restart nginx
ok "Nginx proxy enabled"

# ---------- Post checks ----------
say "Post-check: show proxmox/go.d log hints (journald)"
journalctl -u netdata --no-pager -n 120 | grep -i -E "proxmox|go.d|error|fail|unauth" || true

echo
ok "DONE"
echo "Access Netdata at:  http://<PROXMOX_IP>${NETDATA_PATH}/"
echo "Login: ${HTTP_USER}"
echo
echo "VM/LXC host-side charts should appear after ~30-60 seconds."
echo "In Netdata UI, search for: proxmox, qemu, lxc"
echo
echo "If you want INSIDE-VM monitoring (processes, fs, services), install Netdata in each VM:"
echo "  sudo bash <(curl -sL https://my-netdata.io/kickstart.sh) --dont-wait"
