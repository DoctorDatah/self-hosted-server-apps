# Add a server to Coolify via SSH (step-by-step)

Goal: connect a remote Linux server to Coolify using SSH key auth so Coolify can install Docker/agent and deploy apps.

## Prereqs
- Server is reachable from the Coolify VM (IP/port 22).
- Root SSH access (or a sudo user if you prefer).
- On the server: `openssh-server` running.
- If using a non-root user, it must have **passwordless sudo**. Coolify runs setup commands with `sudo` and cannot enter a password.

---



## 1) Get the Coolify public SSH key
In Coolify UI: `Resources -> Servers -> + Add Server -> Bring your own server -> SSH Key (dropdown)`.
Use **Generate Key** (or **Add New Key**) to create it in the UI, then click **View Public Key** to copy it.

If you prefer CLI, generate a key on the Coolify VM instead:
```bash
mkdir -p /data/coolify/ssh/keys
ssh-keygen -t ed25519 -f /data/coolify/ssh/keys/coolify_key -N "" -C "coolify@server"
cat /data/coolify/ssh/keys/coolify_key.pub
```
Copy the full public key (starts with `ssh-ed25519`).

---

## 2) On the target server, enable SSH and add the key
Install SSH if needed:
```bash
apt update
apt install -y openssh-server
systemctl enable --now ssh
```

Add the Coolify public key for **root** (if you will connect as `root`):
```bash
mkdir -p /root/.ssh
chmod 700 /root/.ssh
echo "PASTE_COOLIFY_PUBLIC_KEY" >> /root/.ssh/authorized_keys
chmod 600 /root/.ssh/authorized_keys
chown root:root /root/.ssh/authorized_keys
systemctl restart ssh
```

Add the Coolify public key for a **non-root user** (example: `malik`):
```bash
mkdir -p /home/malik/.ssh
chmod 700 /home/malik/.ssh
echo "PASTE_COOLIFY_PUBLIC_KEY" >> /home/malik/.ssh/authorized_keys
chmod 600 /home/malik/.ssh/authorized_keys
chown malik:malik /home/malik/.ssh/authorized_keys
systemctl restart ssh
```

---

## 3) On the target Server: allow passwordless sudo (non-root users only)
If you will connect as a non-root user (example: `malik`), you must allow NOPASSWD sudo first.
Coolify runs setup commands with `sudo` in a non-interactive session, so password prompts will fail.

Run this on the target VM (the server you’re adding to Coolify):
```bash
sudo visudo
```
Add this line:
```
malik ALL=(ALL) NOPASSWD:ALL
```
Replace `malik` with your username. If you will connect as `root`, you can skip this step.

---

## 4) Test SSH from the Coolify VM
```bash
ssh -i /data/coolify/ssh/keys/coolify_key root@SERVER_IP "echo SSH OK"
```
If you see `SSH OK`, the key works.

If you are using a non-root user:
```bash
ssh -i /data/coolify/ssh/keys/coolify_key malik@SERVER_IP "echo SSH OK"
```

---

## 5) Add the server in the Coolify UI
`Resources -> Servers -> + Add Server -> Bring your own server (Remote Server via SSH)`

Use:
- Host/IP: `SERVER_IP`
- User: `root` (or `malik` if you added the key to that user)
- Port: `22`
- SSH Key: the key you generated/selected
- Password: leave empty

Coolify will connect, install Docker if needed, and deploy its agent.

---

## 6) Firewall quick check (if using UFW)
```bash
ufw allow 22/tcp
ufw reload
```

---

## Common issues
- Wrong IP/port: verify `ssh root@SERVER_IP` works from the Coolify VM.
- Bad permissions: `/root/.ssh` must be `700`, `authorized_keys` must be `600`.
- Key mismatch: make sure the key pasted matches the one selected in the UI.
- Permission denied (publickey,password): user mismatch or key is in the wrong home directory (e.g., key added to `/root` but Coolify user is `malik`).
- Sudo password prompt error: the SSH user needs NOPASSWD sudo or use `root`.
- Host key errors: remove the IP from known_hosts and try again:
  ```bash
  sed -i "/SERVER_IP/d" /root/.ssh/known_hosts
  ```
