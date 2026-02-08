# Repo Clone + Update Guide (VM)

## Summary
- **Goal:** Clone this repo onto the VM and pull updates later.
- **Scope:** VM-side steps only.

## Preconditions
- VM has Git installed (`git --version` works).
- You have network access to GitHub.

## Variables
| **Name** | **Example** | **Notes** |
| --- | --- | --- |
| `REPO_URL` | `https://github.com/DoctorDatah/self-hosted-server-apps` | Use SSH if preferred. |
| `REPO_DIR` | `/home/malik/self-hosted-server-apps` | Always clone as the `malik` user (not root). |

## Clone or Update Steps (VM)
1) SSH to the VM as `malik`. (or through proxmos terminal)
2) Clone the repo (first time):
```bash
sudo -u malik git clone https://github.com/DoctorDatah/self-hosted-server-apps /home/malik/self-hosted-server-apps
```
When prompted: username = `doctordatah`, password = your PAT.

3) If you see “already exists and is not an empty directory”, the repo is already there:
```bash
cd /home/malik/self-hosted-server-apps
git pull
```

4) Verify the repo exists:
```bash
ls -la /home/malik/self-hosted-server-apps
```

## HTTPS + PAT (Option 1)
GitHub no longer supports password auth for Git over HTTPS. Use a Personal Access Token (PAT):
1) Create a PAT in GitHub:
   - GitHub → Settings → Developer settings → Personal access tokens
   - Public repo: no scopes needed
   - Private repo: `repo` scope
2) Clone and use the token as the password:
```bash
sudo -u malik git clone https://github.com/DoctorDatah/self-hosted-server-apps /home/malik/self-hosted-server-apps
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
cd /home/malik/self-hosted-server-apps
git pull
```
