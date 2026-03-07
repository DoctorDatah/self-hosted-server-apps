# USER GUIDE

## Config location

All machine/target configuration is under `vm-configs/`:
- `vm-configs/vm-machines.yaml`
- Optional legacy files:
  - `vm-configs/vm-operations.yaml`
  - `vm-configs/vm-env-rules.yaml`

## Operating modes

1. Manual inside VM: `./runtime/vmcx run ... --exec-mode local`
2. Operator control machine: `vmcx run ... --exec-mode ssh`
3. GitHub Actions wrappers: workflows call `_vm-codex-v2-execute.yml`

## Common commands

```bash
./runtime/vmcx list-targets
./runtime/vmcx list-aliases
./runtime/vmcx plan --target n8n-stage-1 --stages vm_install --exec-mode local
./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local
./runtime/vmcx run-group --group prod-app-vms --stages backup_app --concurrency 1 --confirm --exec-mode ssh
```

## Run inspection

```bash
./runtime/vmcx status --run-id <id>
./runtime/vmcx resume --run-id <id>
./runtime/vmcx cancel --run-id <id>
```
