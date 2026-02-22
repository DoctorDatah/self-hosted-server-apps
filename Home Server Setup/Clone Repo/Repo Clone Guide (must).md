# Repo Clone + Update Guide (Debian VM)

## Summary
- **Goal:** Clone this repo onto the VM and pull updates later.
- **Scope:** VM-side steps only (Debian 13).

## Preconditions
- VM has Git installed (`git --version` works).
- You have network access to GitHub.

## Per-VM Workflow (Order)
Use this order for a new VM:
1) Install prerequisites (`/root/self-hosted-server-apps/Home Server Setup/Installations/install_all.sh`).
2) Clone this repo.
3) Deploy the app stack (e.g., Coolify or other app). It should attach to the shared `appnet` network.
4) Run Cloudflare Tunnel (see `Home Server Setup/Cloudflare` scripts).
5) Follow the post-setup guide to map the tunnel to the app network.

## Variables
| **Name** | **Example** | **Notes** |
| --- | --- | --- |
| `REPO_URL` | `https://github.com/DoctorDatah/self-hosted-server-apps` | Use SSH if preferred. |
| `REPO_DIR` | `/root/self-hosted-server-apps` | Clone location on this host. |

## Clone or Update Steps (VM)
1) SSH to the VM as root (or use the Proxmox console).
2) Install Git if missing:
```bash
apt-get update && apt-get install -y git
```
3) Quick setup to avoid repeated auth prompts:
```bash
cd /root
git config --global credential.helper store
```
4) Clone the repo (first time):
```bash
git clone https://github.com/DoctorDatah/self-hosted-server-apps /root/self-hosted-server-apps
```
When prompted: username = `doctordatah`, password = your PAT.

5) If you see “already exists and is not an empty directory”, the repo is already there:
```bash
cd /root/self-hosted-server-apps
git pull
```

6) Verify the repo exists:
```bash
ls -la /root/self-hosted-server-apps
```

## HTTPS + PAT (Option 1)
GitHub no longer supports password auth for Git over HTTPS. Use a Personal Access Token (PAT):
1) Create a PAT in GitHub:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Public repo: no scopes needed
   - Private repo: `repo` scope
2) Clone and use the token as the password:
```bash
git config --global credential.helper store
git clone https://github.com/DoctorDatah/self-hosted-server-apps /root/self-hosted-server-apps
```
When prompted:
- Username: `doctordatah`
- Password: paste your PAT (In IOS passwords)

## Troubleshooting
- **Git not installed:** `sudo apt-get update && sudo apt-get install -y git`
- **HTTPS auth failed:** Use a PAT as the password (see HTTPS + PAT section).
- **Auth errors (SSH):** Ensure your VM has access to your SSH key and GitHub.
- **Permission denied (HTTPS):** Use a personal access token if required.

## Update Later
Pull updates from inside the repo:
```bash
cd /root/self-hosted-server-apps
git pull
```
