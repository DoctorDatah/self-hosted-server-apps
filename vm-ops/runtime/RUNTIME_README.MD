# RUNTIME_README.MD

## 0. In Plain English (What and Why)
`runtime/` is the brain of vm-ops.

What this means in real life:
- You run one command tool (`vmcx`) for plan/run/status.
- The runtime reads config, checks policy, and runs stages.

Why this exists:
- Keeps behavior consistent across local, SSH, and CI.
- Avoids duplicate logic in scripts/workflows.

## 0.1 First-Time User Start Here
1. Run `./runtime/vmcx doctor --ci`.
2. Run `./runtime/vmcx list-targets` and `list-aliases`.
3. Run `plan` before `run`.

## 0.2 Common Beginner Mistakes
- Mistake: Running `run` without `plan`.
  Fix: Always preview first.
- Mistake: Expecting alias to run if target does not enable stage.
  Fix: Check `vm-configs/vm-machines.yaml` `enabled_setups` (or `enabled_stages`).

## 0.3 Edit vs Do Not Edit
- Edit runtime code only for orchestration engine changes.
- Do not move stage business logic here.

## 1. What This Folder Is About
The `runtime/` folder is the execution engine for vm-ops.

It provides one CLI (`vmcx`) and one orchestration path for:
- local execution,
- SSH execution,
- and CI-triggered execution.

## 2. What It Holds
Current components:
- `runtime/vmcx`: main CLI entrypoint.
- `runtime/lib/`:
  - `io_utils.py` for file/load/merge utilities,
  - `resolve.py` for target/alias/stage/params resolution,
  - `runner.py` for run lifecycle and status handling.
- `runtime/executors/`:
  - `local.py` for local stage execution,
  - `ssh.py` for remote stage execution.
- `runtime/planner/plan.py` for plan formatting.
- `runtime/tests/test_plan_and_doctor.sh` smoke check.

## 3. How It Relates to Other Components
Runtime sits in the middle of the entire architecture:
- Reads definitions from `vm-configs/vm-machines.yaml` and `apps/`.
- Optional legacy inputs: `vm-configs/vm-operations.yaml`, `vm-configs/vm-env-rules.yaml`.
- Executes `vm-setups/*/stage.sh` through local or SSH executors.
- Uses helpers from `tools/` when needed (repo ensure, secret resolution).
- Writes run artifacts to `local-state/runs/<run-id>/`.
- Is called directly by operators, by ai-skills, and by GitHub Actions workflows.

## 4. How Users Can Use It and What For
Use `runtime/vmcx` for all controlled operations.

### Common commands
- Validate:
  - `./runtime/vmcx doctor --ci`
- Discover:
  - `./runtime/vmcx list-targets`
  - `./runtime/vmcx list-groups`
  - `./runtime/vmcx list-aliases`
- Plan:
  - `./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh`
- Execute:
  - `./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh`
- Multi-target:
  - `./runtime/vmcx run-group --group prod-app-vms --stages backup_app --concurrency 1 --confirm --exec-mode ssh`
- Run lifecycle:
  - `./runtime/vmcx status --run-id <id>`
  - `./runtime/vmcx resume --run-id <id>`
  - `./runtime/vmcx cancel --run-id <id>`

### Beginner-safe operating pattern
1. Always run `doctor` first.
2. Always run `plan` before `run`.
3. Start with staging target.
4. Use prod only after staging success.

### Troubleshooting checklist
- "Unknown alias/target": check `vm-configs/vm-machines.yaml` (`set_of_operations`) and optional `vm-configs/vm-operations.yaml`.
- "Stage not enabled": check target `enabled_setups` / `enabled_stages`.
- "Policy denies": check optional `vm-configs/vm-env-rules.yaml`.
- "SSH failure": check target SSH config and secret refs.

## 5. Examples
### Example: Safe execution sequence
```bash
./runtime/vmcx doctor --ci
./runtime/vmcx plan --alias n8n-vm-install --exec-mode local
./runtime/vmcx run  --alias n8n-vm-install --stages vm_install --confirm --exec-mode local
```

### Example: Debug failed run
```bash
./runtime/vmcx status --run-id run-2026-03-06-000001-123
sed -n '1,220p' local-state/runs/run-2026-03-06-000001-123/01-vm_install.log
```

## 6. Expansion Factor (How This Scales)
Runtime is designed to scale by reusing one engine for many targets and interfaces.

Scale pattern:
- More targets/apps should mostly mean config growth (`vm-configs/vm-machines.yaml`, `apps/`), not runtime rewrites.
- Add stages for new operation domains; keep runtime generic.
- Keep one execution path for local, SSH, and CI.

If you add many VMs:
- Use `run-group` with controlled concurrency.
- Monitor run IDs and logs in `local-state/`.
- Keep runtime changes backward-compatible with existing stage contracts.
