# VM Install Tools

This folder contains scripts to install common VM prerequisites.

## Quick Start
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Installations/install_all.sh"

```
After install, log out and log back in as `malik` so the docker group change applies.

## Run Specific Tools
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/Installations/install_all.sh" --only docker,git,python
```

## Scripts
Scripts live in `scripts/`:
- `scripts/docker.sh` installs Docker Engine + Docker Compose plugin
- `scripts/git.sh` installs Git
- `scripts/infisical.sh` installs the Infisical CLI
- `scripts/network.sh` creates the shared `appnet` Docker network
- `scripts/python.sh` installs Python3 + pip
- `scripts/utils.sh` installs curl + wget

## Versions
Pinned version placeholders live in `requirements.txt`. Update if you want to track specific versions.
