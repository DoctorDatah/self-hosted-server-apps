# Homelab Knowledge Base — Proxmox, VMs, Backups, Reverse Proxy, DNS, and IP Layers

This guide consolidates the core concepts for running a secure, resilient homelab with Proxmox, internal VMs, backups, reverse proxying, DNS, and networking. Use it as a ready reference when configuring, troubleshooting, or explaining your setup.

---

## 1) Understanding Network & IP Layers (Most Important Concept)

Your home network and servers operate on two different IP layers:

### 🌍 Public IP (WAN IP)
- Internet-visible address assigned by your ISP (e.g., `45.79.214.32`).
- Dynamic by default—can change after router reboots, ISP lease renewals, or hardware changes.
- DNS records must point here; DNS only uses public addresses.
- **Never** configure this IP on Proxmox or VMs for normal home hosting; it belongs to the router’s WAN interface.

### 🏷 Router IP (LAN Gateway IP / Internal Router Admin IP)
- Private internal address for your router (common examples: `192.168.1.1`, `10.0.0.1`, `192.168.0.1`).
- Used as the default gateway for your LAN and for router administration (Wi‑Fi settings, port forwarding, device lists, etc.).
- Not reachable from the public internet.

### 🖥 Local Device / VM IPs
- Private LAN addresses from DHCP or static assignment (e.g., `192.168.1.10`, `192.168.1.50`, `10.0.0.20`).
- Remain stable even if the public IP changes.
- Used for VM-to-VM communication, reverse proxy upstreams, and local SSH access.

**Key rule:**  
DNS → public IP only.  
Router → forwards ports to local VM IPs.  
VMs and Proxmox stay on the private LAN and do not change when the WAN IP changes.

---

## 2) Proxmox Host (Hypervisor) Configuration & Security
- Keep the Proxmox host private on the LAN; do **not** expose it to the internet.
- Default networking uses a Linux bridge (`vmbr0`) to place VMs on your LAN.
- The host does not block VM traffic unless you enable the Proxmox firewall.
- Recommended hardening:
  - Enable Proxmox 2FA for admin accounts.
  - Use strong passwords or SSH keys.
  - Restrict management access to VPN only if remote access is required.

---

## 3) Hosting Services on VMs & Public Accessibility

Expose services from VMs—not from the Proxmox host.

### A) Router Port Forwarding (Most common)
- Router receives traffic on your public IP.
- Forward required ports to the reverse proxy VM, e.g.:
  - TCP 80 → `192.168.1.10`
  - TCP 443 → `192.168.1.10`

### B) Reverse Proxy inside a VM
- Run Nginx, Caddy, or Traefik in a VM that listens on ports 80/443.
- Route requests to internal services:
  - `app1.domain.com → 192.168.1.50:3000`
  - `app2.domain.com → 192.168.1.60:4000`
- The proxy manages TLS certificates and routing rules; internal services remain on private IPs.

**Key rule:** Expose apps, not hypervisors.

---

## 4) VM-Level Firewalling (Optional but recommended)

Enable UFW or iptables inside each VM to limit exposed ports:

```bash
sudo ufw enable
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

Open only the ports required by the VM’s services. This is independent of the Proxmox firewall.

---

## 5) Backup Strategy (Aligned to Available Storage)

Storage layout:
- VM runtime disk: **250GB**
- Local backup disk: **2TB HDD**
- Off-site storage: **2TB Google Drive quota**

What to back up:
- Full VM backups (vzdump/PBS) for fast restores.
- Database dumps for data-only recovery.
- Config files for quick rebuilds.

Where to store backups (avoid the 250GB VM disk):
```
/mnt/backups/
   ├── vms/
   ├── databases/
   └── files/
```

---

## 6) Rclone Basics (Off-site Sync to Google Drive)

**What Rclone is:** A terminal tool for copying/syncing files to cloud storage using named remotes.

**Auth without a browser on the server:**
1. Run `rclone config`.
2. Choose no-browser auth; leave client ID/secret blank.
3. Rclone prints a URL and verification code—open the URL on any device and paste the code back.
4. Rclone stores the OAuth token locally.

**Recommended mode for backups:**
Use `copy` so Drive accumulates files:
```bash
rclone copy /mnt/backups gdrive:/ProxmoxBackups \
  --drive-chunk-size 64M \
  --log-file=/var/log/rclone-homelab.log
```

Automate via cron:
```cron
0 3 * * * rclone copy /mnt/backups gdrive:/ProxmoxBackups --drive-chunk-size 64M --log-file=/var/log/rclone.log
```

---

## 7) Handling an Unplugged Backup Disk

Scenario | Result
--- | ---
Drive unplugged | Backup jobs fail temporarily; existing data on disk is safe.
Drive reconnected | Backups remain; remount and continue.
Device name changes | Possible if mounting by `/dev/sdX`.

**Fix:** Mount by UUID with `nofail` to survive boot without the disk:
```fstab
UUID=your-uuid /mnt/backups ext4 defaults,nofail 0 2
```

---

## 8) Dynamic Public IP Changes — What breaks and what doesn’t

Component | Affected by public IP change?
--- | ---
DNS mapping | ✔ Yes — update required.
Proxmox host IP | ❌ No change.
VM internal IPs | ❌ No change.
Reverse proxy config | ❌ No change.
Firewall in VM | ❌ No change.
Backups on HDD | ❌ Still present.
Backups in Google Drive | ❌ Still present.

**How to fix access when the public IP changes:**
- Update the DNS A record manually, **or**
- Use DDNS automation to update DNS automatically.
- No changes needed on Proxmox or the VMs.

---

## Final Takeaway

1) Domain → DNS → **Public IP** (update if it changes).  
2) Public IP → **Router port-forwarding** → reverse proxy VM (private IP).  
3) Reverse proxy → routes to **internal services**.  
4) Backups → stored on **2TB HDD** → copied to **Google Drive via Rclone**.  
5) Hardware issues or unplugged drives do not erase existing backups; remount and continue.

Keep the hypervisor private, expose only application endpoints via the reverse proxy, and protect your data with layered backups.
