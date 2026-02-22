## Disable Proxmox Enterprise Repos (No Subscription)

### 1) Run the fix (root shell)

```bash
set -e

# Disable any enterprise repos
for f in /etc/apt/sources.list.d/*; do
  [ -e "$f" ] || continue
  if grep -q "enterprise.proxmox.com" "$f" 2>/dev/null; then
    echo "Disabling enterprise repo: $f"
    mv -v "$f" "$f.disabled"
  fi
done

# Add PVE no-subscription repo
cat > /etc/apt/sources.list.d/pve-no-subscription.list <<'EOF'
deb http://download.proxmox.com/debian/pve trixie pve-no-subscription
EOF

# Add Ceph no-subscription repo (safe even if unused)
cat > /etc/apt/sources.list.d/ceph-no-subscription.list <<'EOF'
deb http://download.proxmox.com/debian/ceph-squid trixie no-subscription
EOF

# Refresh and upgrade
apt clean
apt update
apt full-upgrade -y
apt autoremove --purge -y

# Confirm enterprise is gone
grep -R "enterprise.proxmox.com" /etc/apt/ || echo "No enterprise repos found. All good!"
```

---

### 2) What this does

* Disables **PVE + Ceph enterprise** repo files (`.list` or `.sources`)
* Enables **public Proxmox no-subscription** repositories
* Updates & upgrades your system safely

---

### 3) Expected `apt update` result

You should only see:

```
deb.debian.org
security.debian.org
download.proxmox.com (no-subscription)
```

And **no 401 Unauthorized errors**

---

### 4) Optional UI fix (removes subscription popup in Proxmox web panel)

Does **not** affect package repos:

```bash
sed -i.bak "s|data.status !== 'Active'|false|g" /usr/share/javascript/proxmox-widget-toolkit/proxmoxlib.js
systemctl restart pveproxy
```

---

If you want, I can also export this guide into a `.sh` script so you can run it on new nodes instantly.
