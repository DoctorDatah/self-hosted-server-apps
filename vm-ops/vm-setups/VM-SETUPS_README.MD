# VM-SETUPS_README.MD

## 0. In Plain English (What and Why)
`vm-setups/` is where the real work happens.

What this means in real life:
- Install, deploy, backup, restore, cleanup are implemented here.
- If behavior changes in operations, this is usually where you edit.

Why this exists:
- Keeps operational logic modular and testable.
- Prevents logic duplication in runtime and CI workflows.

## 0.1 First-Time User Start Here
1. Open one stage folder (for example `vm-setups/vm_install/`).
2. Read `stage.yaml` to know required params.
3. Read `stage.sh` to understand behavior.
4. Test with `plan` then `run` on staging/local first.

## 0.2 Common Beginner Mistakes
- Mistake: Updating `stage.sh` but not `stage.yaml` params.
  Fix: Keep metadata and logic in sync.
- Mistake: Creating duplicate app-specific stages.
  Fix: Prefer reusable stages with params.

## 0.3 Edit vs Do Not Edit
- Edit here for operational behavior changes.
- Do not place policy rules here; use `vm-configs/vm-env-rules/`.

## 1. What This Folder Is About
The `vm-setups/` folder contains the real operational logic.

This is where system mutation happens: install, access config, deploy, cleanup, backup, and restore.

## 2. What It Holds
Current stage set:
- `repo_clone_or_update`
- `vm_install`
- `cloudflare_vm_access`
- `cloudflare_app_access`
- `app_deploy`
- `cleanup_vm`
- `backup_app`
- `restore_app`
- `_common` shared shell helpers (`params.sh`)

Common stage files:
- `stage.sh`: executable logic
- `stage.yaml`: stage contract and metadata
- `README.md`: stage-specific notes
- optional support dirs: `scripts/`, `templates/`, `tests/`, `adapters/`, `manifests/`

## 3. How It Relates to Other Components
- Runtime invokes stages via local or SSH executors.
- Inventory controls stage availability per target.
- Policies constrain when stages may run.
- Profiles and params feed stage inputs.
- Stage outputs and logs end up in `local-state/`.

Runtime provides these environment variables to stages:
- `VMCX_STAGE_ID`
- `VMCX_TARGET_ID`
- `VMCX_EXEC_MODE`
- `VMCX_PARAMS_JSON`
- `VMCX_MERGED_CONFIG_JSON`
- `VMCX_RUN_DIR`
- `VMCX_REPO_ROOT`

## 4. How Users Can Use It and What For
Use this folder whenever operational behavior must be changed.

### Safe stage development workflow
1. Update `stage.sh` logic.
2. Update `stage.yaml` required/optional params.
3. Keep behavior idempotent when possible.
4. Test with `plan` then `run` in staging/local mode.
5. Review run logs in `local-state/runs/<run-id>/`.

### Typical stage commands
- Single stage:
  - `./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local`
- Multi-stage:
  - `./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh`

### Important rules
- Keep business logic in stages, not in workflows/skills.
- Keep sensitive values out of stage scripts and repo files.
- Use params and secret references, not hardcoded credentials.

### Frequent failure reasons
- Missing required params from `stage.yaml`.
- External dependency missing (docker, ssh, etc.).
- Policy deny.
- Stage not enabled for the target.

## 5. Examples
### Example: Run one stage directly
```bash
./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local
```

### Example: Run restore with params
```bash
./runtime/vmcx run --alias n8n-app-restore-staging --params '{"backup_id":"bkp-2026-03-06-001"}' --confirm --exec-mode ssh
```

### Example: Stage metadata shape (`stage.yaml`)
```yaml
{
  "stage_id": "app_deploy",
  "entrypoint": "stage.sh",
  "required_params": ["app_id"],
  "supports_exec_modes": ["local", "ssh"]
}
```

## 6. Expansion Factor (How This Scales)
Stages are where operational capability scales.

Scale pattern:
- Add new stage folders for new operation domains.
- Keep each stage focused and testable.
- Reuse `_common` helpers for shared parsing/utility logic.

If you add more VMs/apps:
- Prefer reusing existing stages with params over creating app-specific duplicate stages.
- Add adapters/templates when needed, but keep core stage contracts stable.
- Keep stage metadata (`stage.yaml`) accurate so runtime validation remains reliable.
