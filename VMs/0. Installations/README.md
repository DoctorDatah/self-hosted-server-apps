# VM Install Tools

This folder contains scripts to install common VM prerequisites.

## Quick Start
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/0. Installations/install_all.sh"
```

## Run Specific Tools
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/0. Installations/install_all.sh" --only docker,git,python
```

## Scripts
Scripts live in `scripts/`:
- `scripts/docker.sh` installs Docker Engine + Docker Compose plugin
- `scripts/git.sh` installs Git
- `scripts/python.sh` installs Python3 + pip

## Versions
Pinned version placeholders live in `requirements.txt`. Update if you want to track specific versions.
