# SPINUP-GUIDE-README.md

This guide gets `vm-ops` and `vm-managment-app` running on a host or VM with copy/paste commands.

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

If install fails with DNS/network errors, your machine cannot reach PyPI yet. Fix outbound internet/DNS, then rerun the two commands above.

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

If still not reachable, check listener on VM:

```bash
ss -ltnp | grep 8787 || lsof -iTCP:8787 -sTCP:LISTEN
```

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
