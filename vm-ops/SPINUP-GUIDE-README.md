# SPINUP-GUIDE-README.md

This guide gets `vm-ops` and **VM Management** (`vm-managment-app` folder) running on a host or VM with copy/paste commands.

## 1. Clone Repo

```bash
cd ~
git clone <YOUR_REPO_URL> self-hosted-server-apps
cd self-hosted-server-apps
git checkout feat/codex_vm_v1
```

## 2. Enter vm-ops

```bash
cd vm-ops
```

From this point onward, commands assume your current directory is:

```text
.../self-hosted-server-apps/vm-ops
```

For VM-hosted runtime path alignment (no `vm-ops/vm-ops` nesting), use:

```bash
sudo mkdir -p /repo
sudo chown -R "$USER":"$USER" /repo
git clone <YOUR_REPO_URL> /repo
cd /repo/vm-ops
```

Then keep machine `repo_path` set to:

```text
/repo/vm-ops
```

## 3. Verify Python

```bash
python3 --version
```

If Python is missing:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-venv python3-pip
```

## 4. Create Virtual Environment

```bash
python3 -m venv vm-managment-app/.venv
source vm-managment-app/.venv/bin/activate
python --version
pip --version
```

## 5. Install UI Dependencies

```bash
pip install --upgrade pip
pip install -r vm-managment-app/requirements.txt
```

If you are still at repo root (`.../self-hosted-server-apps`) instead of `vm-ops`, use:

```bash
pip install --upgrade pip
pip install -r vm-ops/vm-managment-app/requirements.txt
```

If install fails with DNS/network errors, your machine cannot reach PyPI yet. Fix outbound internet/DNS, then rerun the two commands above.

## 5.1 Install System Dependencies For Git/PR Features

Linux (Ubuntu/Debian):

```bash
sudo apt-get update
sudo apt-get install -y git gh
gh --version
gh auth login
gh auth status
```

macOS (Homebrew):

```bash
brew install gh
gh --version
gh auth login
gh auth status
```

Without `gh`, Branch/Commit PR actions in the UI will show an error.
If `gh` is installed but UI still cannot find it, start server with:

```bash
GH_BIN=$(which gh) uvicorn app.main:app --app-dir vm-managment-app --reload --host 127.0.0.1 --port 8787
```

## 6. Validate Repo

```bash
python3 tools/quick_validate.py
./runtime/vmcx doctor --ci
```

Expected result: both should report `status: ok`.

## 7. Run Local UI

```bash
uvicorn app.main:app --app-dir vm-managment-app --reload --host 127.0.0.1 --port 8787
```

Open in browser:

```text
http://127.0.0.1:8787
```

## 8. If You Are Running On A Remote VM

`127.0.0.1` points to the VM itself, not your laptop browser.

Start server on all interfaces:

```bash
uvicorn app.main:app --app-dir vm-managment-app --reload --host 0.0.0.0 --port 8787
```

Then use one of these access methods:

1. SSH tunnel (recommended)

```bash
ssh -L 8787:127.0.0.1:8787 <user>@<vm-ip>
```

Open on laptop:

```text
http://127.0.0.1:8787
```

2. Direct VM IP (only if firewall/security group allows port `8787`)

```text
http://<vm-ip>:8787
```

Example direct URL (replace with your real VM IP):

```text
http://87.87.87.87:8787
```

If still not reachable, check listener on VM:

```bash
ss -ltnp | grep 8787 || lsof -iTCP:8787 -sTCP:LISTEN
```

Important:
- `0.0.0.0` is only a bind address for the server command.
- Never paste `http://0.0.0.0:8787` into Safari/Chrome.

## 9. Useful Runtime Checks

```bash
./runtime/vmcx list-targets
./runtime/vmcx list-aliases
./runtime/vmcx plan --alias n8n-vm-install --exec-mode local
./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh
```

## 10. Deactivate Venv

```bash
deactivate
```
