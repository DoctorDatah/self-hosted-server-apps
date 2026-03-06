# vm-codex

Skills-first VM operations runtime.

No API stack is included; all operations run through local `vmcx` + skills.

## Core Model

- Use Codex skills as the operator interface.
- Execute local runtime commands via `./vm-codex/runtime/vmcx`.
- Resolve target variability from inventory and layered profiles.
- Run in plan-first mode, then apply only with explicit confirmation.

## Main Components

- Runtime CLI: `vm-codex/runtime/vmcx`
- Inventory: `vm-codex/inventory/targets.yaml`
- Alias shortcuts: `vm-codex/inventory/aliases.yaml`
- Profiles: `vm-codex/profiles/base` and `vm-codex/profiles/overlays`
- Requirements: `vm-codex/requirements/global.yaml`, `roles/*`, `targets/*`
- Stage executors: `vm-codex/runtime/stages/*.sh`
- Local run state/logs: `vm-codex/local-state/`
- Skills: `vm-codex/skills/vm-codex-*`

## Install Skills Into Codex Home

```bash
./vm-codex/tools/install_skills.sh
```

## Runtime Commands

```bash
./vm-codex/runtime/vmcx list-targets
./vm-codex/runtime/vmcx list-groups
./vm-codex/runtime/vmcx list-aliases

./vm-codex/runtime/vmcx plan --alias n8n-vm-setup
./vm-codex/runtime/vmcx run --alias n8n-vm-setup --confirm

./vm-codex/runtime/vmcx run-group --group app-tier --stages vm_install --concurrency 2 --confirm
```

## Operator Guide

Use the full goal-focused guide:
- [USER_GUIDE.md](/Users/hassan/self-hosted-server-apps/vm-codex/USER_GUIDE.md)
