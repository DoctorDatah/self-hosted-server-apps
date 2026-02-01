# Coolify ↔ Proxmox Ubuntu VM (SSH key setup)

Goal: let Coolify connect to an Ubuntu VM on Proxmox via SSH key auth, so it can install Docker and its agent without passwords.

## Network requirements (assumed ready)
- VM IP reachable from the Coolify VM
- SSH port open (default 22)
- Root access available (keys go in `/root/.ssh`)

---

## 1) On the Coolify VM — copy the public key (UI)
In Coolify: `Servers → Add Server → Bring your own server → SSH Key (dropdown) → View Public Key`. Copy the full key (starts with `ssh-ed25519 AAAA...`).
If the dropdown is empty, generate a key first:
```bash
mkdir -p /data/coolify/ssh/keys
ssh-keygen -t ed25519 -f /data/coolify/ssh/keys/coolify_proxmox_key -N "" -C "coolify@proxmox"
cat /data/coolify/ssh/keys/coolify_proxmox_key.pub
```
Then copy that public key.

---

## 2) On the Ubuntu VM (Proxmox guest) — install and configure SSH
Install SSH if missing:
```bash
apt update
apt install -y openssh-server
systemctl enable --now ssh
```
Enable key auth and disable passwords:
```bash
sed -i 's/#*PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl restart ssh
```

---

## 3) Still on the Ubuntu VM — add Coolify's public key to root
```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "PASTE_YOUR_COOLIFY_PUBLIC_KEY_HERE" | tee -a /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown root:root /root/.ssh/authorized_keys
systemctl restart ssh
```
Replace `PASTE_YOUR_COOLIFY_PUBLIC_KEY_HERE` with the key you copied. Verify permissions:
```bash
stat -c "%a %n" /root/.ssh /root/.ssh/authorized_keys
```
Expected:
```
700 /root/.ssh
600 /root/.ssh/authorized_keys
```

---

## 4) On the Coolify VM — test SSH to the Ubuntu VM
```bash
ssh -i /data/coolify/ssh/keys/coolify_proxmox_key root@<vm-ip> "echo SSH OK"
```
If you see `SSH OK`, the key works. If not, recheck: correct key pasted, permissions 700/600, correct user, and SSH restarted.

---

## 5) (Recommended) Install Docker on the Ubuntu VM before adding to Coolify
```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
docker ps
```

---

## 6) In Coolify UI — add the server
Navigate: `Resources → Servers → + Add Server → Bring your own server (Remote Server via SSH)`.
Use:
- Host/IP: `<vm-ip>`
- User: `root`
- Port: `22`
- SSH Key: `coolify_proxmox_key` (or the key you picked)
- Password: leave empty

Coolify will connect over SSH, install Docker if needed, deploy its agent, and mark the server ready.

---

## 7) Firewall check on the Ubuntu VM (if using UFW)
```bash
ufw allow 22/tcp
ufw reload
```

---

## 8) Optional — reset known hosts on the Coolify VM after retries
```bash
sed -i "/<vm-ip>/d" ~/.ssh/known_hosts
```

---

## Final checklist
- Public key is in `/root/.ssh/authorized_keys`
- `/root/.ssh` is `700`; `authorized_keys` is `600`; owner `root:root`
- SSH restarted (`systemctl restart ssh`)
- Test SSH from Coolify prints `SSH OK`
- Coolify UI uses the same user and key (`root` + `coolify_proxmox_key`)

If you want next steps, I can provide: (1) a Proxmox cloud-init template with this key preinstalled, or (2) a Coolify bulk-add script for multiple Proxmox VMs.
