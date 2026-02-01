# 🔐 SSH Key Guide — Key `n8n-vm-github`

## Step 1 (Optional) Wipe and verify it's cleared

### Safe wipe (backup first)

```bash
#!/usr/bin/env bash
set -euo pipefail
SSH_DIR="${HOME}/.ssh"

echo "🍯 Backing up..."
STAMP=$(date +%Y%m%d-%H%M%S)
mkdir -p "$SSH_DIR/backup-$STAMP"
cp -a "$SSH_DIR"/* "$SSH_DIR/backup-$STAMP/" 2>/dev/null || true
echo "Backup saved → $SSH_DIR/backup-$STAMP"

echo "🧼 Wiping SSH folder..."
rm -rf "$SSH_DIR"/*
mkdir -p "$SSH_DIR"
chmod 700 "$SSH_DIR"

echo "🔑 Clearing ssh-agent..."
ssh-add -D 2>/dev/null || true

echo "Done ✔"
```

Run:

```bash
bash wipe-ssh.sh
```

### Verify it's empty

```bash
ls -la ~/.ssh
```

You should only see:

```
.  ..
```

## Step 2 Decide the key name + set variables

You already decided:

* Key name: `n8n-vm-github`
* Label/comment: `n8n-vm-github`

Set variables:

```bash
KEYFILE=~/.ssh/n8n-vm-github
PUBFILE="${KEYFILE}.pub"
```

## Step 3 Create the keypair

*(Can be generated in 3 places — Local / Server / Client)*

### A) Generate on Local machine

```bash
ssh-keygen -t ed25519 -C "n8n-vm-github" -f "$KEYFILE"
```

### B) Generate on the Server

```bash
ssh-keygen -t ed25519 -C "n8n-vm-github" -f ~/.ssh/n8n-vm-github
cat ~/.ssh/n8n-vm-github.pub >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### C) Generate on another Client

```bash
ssh-keygen -t ed25519 -C "n8n-vm-github" -f ~/.ssh/n8n-vm-github
chmod 600 ~/.ssh/n8n-vm-github*
```

## Step 4 Keys are created → Verify them

```bash
ls -l ~/.ssh
cat "$PUBFILE"
ssh-keygen -lf "$PUBFILE"
```

You should see your files including:

```
n8n-vm-github
n8n-vm-github.pub
```

## Step 5 Copy key to Server (all options)

### Option 1 — ssh-copy-id (easiest)

```bash
ssh-copy-id -i "$PUBFILE" user@server
```

### Option 2 — Manual append (if shell access)

```bash
cat "$PUBFILE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### Option 3 — Copy via scp

```bash
scp -i "$KEYFILE" "$PUBFILE" user@server:~/.ssh/
ssh user@server "cat ~/.ssh/n8n-vm-github.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Option 4 — Copy via rsync

```bash
rsync -e "ssh -i $KEYFILE" "$PUBFILE" user@server:~/.ssh/
ssh user@server "cat ~/.ssh/n8n-vm-github.pub >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

### Option 5 — Copy via echo pipe

```bash
cat "$PUBFILE" | ssh user@server "cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

## Step 6 Copy key to Client (all options)

### Option 1 — via scp

```bash
scp -i "$KEYFILE" "$PUBFILE" clientuser@clienthost:~/.ssh/
```

### Option 2 — Manual copy/paste

```bash
cat "$PUBFILE"
# paste into client ~/.ssh/authorized_keys
```

### Option 3 — Clipboard copy

```bash
pbcopy < "$PUBFILE"                     # macOS
xclip -selection clipboard < "$PUBFILE"  # Linux
clip < "$PUBFILE"                       # Windows Git Bash
```

On the target client append:

```bash
cat "$PUBFILE" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

# Additional Section: 

# Git hub steup both steps needed. 

## Step 1 : Github (Server, public key) to VM runner continer (Client, private key) 

- When the runner connects to GitHub over SSH, the runner is the client (it initiates the connection to clone/push), and GitHub (git@github.com / ssh.github.com) is the server.

- Note: if runner on the same vm. then host name could be the hostIp or 172.... (goole right loopback) or dns like mydomain.com (if host has it)

- that why put public key in the github deplyemtn key


### Generate (if not generated yet)

```bash
ssh-keygen -t ed25519 -C "n8n-vm-github" -f "$KEYFILE"
```

### Show the public key for GitHub

```bash
cat "$PUBFILE"
```

### Add it to GitHub Repo

* Go to: Repo → Settings → Deploy Keys → Add Deploy Key
* Paste the key
* Enable write access only if you need to push

### Clone using deploy key

```bash
GIT_SSH_COMMAND="ssh -i $KEYFILE -o IdentitiesOnly=yes" git clone git@github.com:owner/repo.git
```

## Test connection to GitHub

```bash
ssh -T git@github.com
```

## Client 2 — VM Runner (client, private key) <-> VM (server, public key)  [does not matter if same host or not]


## Step 1 Generate key 

### A
if genrated on vm (server) then add public key to auterized key. 

How: <commands here>
Please copy the ooption from oave section and paste here. 


Step 2: Copy private key and use in the client (vm runner) 
Since the runner is on github. 
copy the key to the secarete that can pass it to the runner.

cat the private key 
put in SSH_PRIVATE_KEY

then the code will use it in the action to pass it the runner. 


