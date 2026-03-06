# VM Codex Installation Engine

Profile-based installer for VM bootstrapping on Ubuntu/Debian, with schema validation, preflight checks, lockfile protection, logging, and checkpoint/resume support.

## Quick Start

```bash
cd /path/to/self-hosted-server-apps
sudo -E ./vm-codex/installation/install_all.sh --profile manual-app-deploy
```

## Common Commands

```bash
# Discover profiles and available tools
./vm-codex/installation/install_all.sh --list-profiles
./vm-codex/installation/install_all.sh --list-tools

# Run a subset with automatic dependency closure
sudo -E ./vm-codex/installation/install_all.sh --profile manual-app-deploy --only docker,git

# Preview execution only
./vm-codex/installation/install_all.sh --profile manual-app-deploy --dry-run

# Resume after interrupted execution
sudo -E ./vm-codex/installation/install_all.sh --profile manual-app-deploy --resume
```

## Folder Layout

- `install_all.sh`: orchestrator and preflight checks.
- `profiles/schema.yaml`: top-level profile schema contract.
- `profiles/*.yaml`: VM profiles.
- `requirements/versions.yaml`: global tool version defaults.
- `scripts/*.sh`: installer modules.
- `.state/<profile>.json`: checkpoint state.
- `logs/<timestamp>-<profile>.log`: run logs.

## Notes

- Profiles can reference environment variable names in `required_env_vars`; do not store secrets in profile files.
- `--only` keeps profile order and auto-adds dependencies.
- If Docker group membership is changed, log out/in so it takes effect.
