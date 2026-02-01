## Proxmox → Ubuntu VM SSH Setup & Troubleshooting (No-Nonsense)

Quick, layered checks to get SSH working on an Ubuntu Server VM running on Proxmox. Follow in order; stop when you find the issue.

---

### 1) Install the SSH server (inside the Ubuntu VM)

```bash
sudo apt update
sudo apt install -y openssh-server
```

### 2) Enable and start the service

```bash
sudo systemctl enable --now ssh
```

* `enable` → start at boot
* `--now` → start immediately

### 3) Confirm the service is healthy

```bash
sudo systemctl status ssh --no-pager
```

* Expect: `Active: active (running)`
* If `inactive`, `failed`, or `disabled`, fix before continuing (restart or reinstall).

### 4) Confirm the daemon is listening on port 22

```bash
sudo ss -tnlp | grep :22
```

Healthy example:

```
LISTEN 0 128 0.0.0.0:22
```

What it means:
* `LISTEN` → accepting connections
* `0.0.0.0:22` → all IPv4 interfaces

If you get **no output** → SSH is not listening.  
If you see only `:::22` → IPv6-only; IPv4 clients may hang. Force IPv4 via `AddressFamily inet` (see step 10).

### 5) Get the correct VM IP (common pitfall)

```bash
hostname -I
# or
ip a
```

Look for `inet 192.168.x.x/24` or `inet 10.x.x.x/24`. Use that IP for SSH.

### 6) Test from your client

```bash
ping -c 3 VM_IP
ssh youruser@VM_IP
```

If `ping` works, the path is good. SSH should connect if the service is healthy.

### 7) If SSH hangs, use verbose mode

```bash
ssh -v youruser@VM_IP
```

Freeze points & meaning:
* **Waiting for server** → SSH service not running/listening.
* **`SSH2_MSG_KEXINIT` sent** → key exchange handshake issue.
* **`Authenticating…`** → auth problem (key/password).
* **`Name does not resolve`** → using hostname instead of IP.

### 8) If the service failed, restart or run foreground

```bash
sudo systemctl restart ssh
# If it still fails:
sudo /usr/sbin/sshd -D
```

Leave the foreground command running, then try SSH from another terminal to see logs immediately.

### 9) If UFW is enabled, allow SSH

```bash
sudo ufw status
sudo ufw allow 22/tcp
```

### 10) Hardening tips (optional but smart)

Edit `/etc/ssh/sshd_config`:

```
PermitRootLogin no
PasswordAuthentication yes   # only if you need password auth
AddressFamily inet           # force IPv4 if IPv6 causes hangs
```

Then:

```bash
sudo systemctl restart ssh
```

---

### Final connection rule

Always connect with the explicit IP:

```bash
ssh USER@IP
```

Example: `ssh terramox@192.168.88.20`

Avoid hostname-based SSH unless DNS is configured.

---

### If you’re still stuck, collect these for diagnosis

```bash
sudo systemctl status ssh --no-pager
sudo ss -tnlp | grep :22
```
