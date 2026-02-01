# SSH made simple

This is a beginner-friendly walkthrough for logging into a server with SSH keys. Goal: get you connecting without passwords, understand what the keys are, and fix common issues.

## What is happening?
- SSH is a secure way for your computer (the client) to talk to another computer (the server) over the network.
- A keypair has two parts: **public key** (safe to share, goes on the server) and **private key** (keep on your machine, do not share).
- When the server sees your public key, it lets your private key prove your identity, so no password is needed.

## Key files at a glance (where they live and what they do)
- **`~/.ssh/id_ed25519` / `id_rsa`** (private key): proves your identity. Stays only on clients you trust.
- **`~/.ssh/id_ed25519.pub` / `id_rsa.pub`** (public key): goes to servers you want to log into. Safe to copy widely.
- **`~/.ssh/authorized_keys`** (on the server): list of public keys allowed to log in as that user. One key per line; the SSH daemon checks this file to decide which public keys are permitted to authenticate.
- **`~/.ssh/known_hosts`** (on the client): fingerprints of servers you have trusted before. Protects you from impostor servers by pinning the server’s host key to its hostname/IP.
- **`~/.ssh/config`** (on the client): optional shortcuts and defaults (hostnames, usernames, ports, which key to use).
- **ssh-agent** (optional helper): keeps unlocked keys in memory so you do not retype passphrases; see “Keep track of keys.”

## Fast mental model: who keeps what
- Golden rule: the **server keeps your public key** (in `~/.ssh/authorized_keys`); the **client keeps your private key** (in `~/.ssh/`).
- Keys can be created wherever convenient, but always end with the private key on the client and the public key on the server.
- If you ever generate a key on the server, copy the private key to the client and delete it from the server so only the client retains it.

## Who holds which key?
- Client-side files live in `~/.ssh/` on your laptop/desktop/automation host.
- Server-side public keys live in the server user’s `~/.ssh/authorized_keys`.
- You can have multiple keypairs for different purposes; each one’s `.pub` can be listed in `authorized_keys`.
- How `authorized_keys` is enforced: when you connect, the server reads this file, picks the matching public key entry, and asks your client to prove possession of the paired private key (no private key ever leaves your client).
- Hostnames and trust: the server identifies itself with a host key; your client pins that fingerprint to the hostname or IP in `~/.ssh/known_hosts`. If the server’s host key changes, SSH warns you to prevent man-in-the-middle attacks.
- If you see a “host key verification failed” error, that is `known_hosts` protecting you—compare the server fingerprint, then remove the stale entry with `ssh-keygen -R <host>`.

## Step 1: make your own keypair (on your computer)
Recommended modern option (ED25519):
```bash
ssh-keygen -t ed25519 -C "your label" -f ~/.ssh/id_ed25519
```
- Press Enter to accept the path; add a passphrase if you want extra protection.
- Files created:
  - `~/.ssh/id_ed25519` (private key, keep secret)
  - `~/.ssh/id_ed25519.pub` (public key, safe to copy)
- Permissions matter: `chmod 700 ~/.ssh` and `chmod 600 ~/.ssh/id_ed25519`.
- Legacy/compatibility (older hosts that lack ED25519):
  ```bash
  ssh-keygen -t rsa -b 4096 -C "your label" -f ~/.ssh/id_rsa
  ```
  Prefer ED25519 unless you know the server only accepts RSA.

## Step 1b: list and inspect your keys (stay organized)
- See what key files exist: `ls -l ~/.ssh`
- Show a public key (safe to share): `cat ~/.ssh/id_ed25519.pub`
- Show a private key’s fingerprint: `ssh-keygen -lf ~/.ssh/id_ed25519`
- If a key has a passphrase, load it into ssh-agent once per session:
  ```bash
  eval "$(ssh-agent -s)"
  ssh-add ~/.ssh/id_ed25519
  ssh-add -l   # list loaded keys
  ```

## Where to generate keys (three common patterns)
1) **Generate on the client (best practice)**
   - Run `ssh-keygen` as above on the client.
   - Copy the public key to the server with `ssh-copy-id` or the manual command below.

2) **Generate on the server, then move the private key to the client** (when the server is the only place you can run commands)
   - On the server:
     ```bash
     ssh-keygen -t ed25519 -C "your label" -f ~/.ssh/id_ed25519
     chmod 700 ~/.ssh && chmod 600 ~/.ssh/id_ed25519
     ```
   - Copy the private key down to the client (run on the client):
     ```bash
     scp user@server:~/.ssh/id_ed25519 ~/.ssh/
     scp user@server:~/.ssh/id_ed25519.pub ~/.ssh/
     chmod 600 ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub
     ```
   - Remove the private key from the server so it lives only on the client:
     ```bash
     ssh user@server "shred -u ~/.ssh/id_ed25519"
     ```

3) **Generate on a third machine (e.g., your laptop), then distribute**
   - Run `ssh-keygen` locally.
   - Copy the public key to each server using the steps below.
   - Keep the private key only on the client(s) that need to connect.

## Step 2: give the server your public key
This lets the server recognize you.
- Easiest (uses your password once):  
  ```bash
  ssh-copy-id -i ~/.ssh/id_ed25519.pub user@server
  ```
- Manual (if ssh-copy-id is missing):  
  ```bash
  cat ~/.ssh/id_ed25519.pub | ssh user@server "mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
  ```
- If the server uses a different port, add `-p <port>` to the SSH/ssh-copy-id command.
- What the server stores: each line of `~/.ssh/authorized_keys` is the public key string (starts with `ssh-ed25519` or `ssh-rsa`, then a long base64 blob, then your label).
- Do **not** copy your private key to the server.

## Step 3: connect with your key
```bash
ssh -i ~/.ssh/id_ed25519 user@server
```
- Different port? `ssh -p 2222 -i ~/.ssh/id_ed25519 user@server`.
- Quick test to see if the key works: `ssh -i ~/.ssh/id_ed25519 user@server "echo logged in"`.

## Optional: shorter commands with ~/.ssh/config
Make a shortcut so you can type `ssh myvm`:
```sshconfig
Host myvm
  HostName 10.0.0.5
  User deploy
  Port 22
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
```
- Save this in `~/.ssh/config`, then `chmod 600 ~/.ssh/config`.

## Copy files with your key
- To server: `scp -i ~/.ssh/id_ed25519 file user@server:/path/`
- From server: `scp -i ~/.ssh/id_ed25519 user@server:/path/file .`
- Sync folders: `rsync -e "ssh -i ~/.ssh/id_ed25519 -p 2222" -av ./dir user@server:/path/`

## Keep track of keys
- See what keys your agent has loaded: `ssh-add -l`
- Add your key to the agent (so you don’t retype passphrases): `ssh-add ~/.ssh/id_ed25519`
- Show a key’s fingerprint (to confirm which key you’re using): `ssh-keygen -lf ~/.ssh/id_ed25519.pub`
- Rotate: make a new keypair, add the new `.pub` to the server, test login, then remove the old key from `authorized_keys`.
- Preferred key types: use ED25519 for new setups; use RSA 4096 only when you must support older SSH servers or hardware that lacks ED25519. Avoid DSA (deprecated) and ECDSA on systems without reliable hardware randomness.

## If it doesn’t work
- Use verbose mode: `ssh -vvv -i ~/.ssh/id_ed25519 user@server`
- Common fixes:
  - Permissions: `chmod 700 ~/.ssh` and `chmod 600 ~/.ssh/authorized_keys`
  - Wrong user or port: retry with the correct username/`-p`
  - Host key changed: `ssh-keygen -R server` then reconnect
  - Public key missing: re-run the copy step and check `authorized_keys` on the server

## Coolify note
- Coolify keeps its SSH keys at `/data/coolify/ssh/keys/` inside the Coolify VM.
- To let Coolify reach another server, copy the relevant `.pub` file from there into that server’s `~/.ssh/authorized_keys`. The private key stays on the Coolify VM.
- For connecting a Proxmox VM to Coolify, see `apps/coolify/proxmox-vm-to-coolify.md`.
