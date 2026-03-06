# vm-managment-app

`vm-managment-app` is a local-only UI for editing VM config files under `vm-ops/vm-configs/`.

## What it edits

- `vm-configs/vm-machines.yaml`
- `vm-configs/vm-operations.yaml`
- `vm-configs/vm-env-rules.yaml`

The YAML files (currently JSON-compatible YAML) remain the source of truth.

## What the app provides

- Table views for machines, operations, and env rules
- Drawer-based forms for nested fields (SSH, params, defaults)
- Validation before save
- Diff preview before save
- Atomic writes (temp file + rename)
- Git status and "prepare branch + commit" action

## Run locally

From `vm-ops/`:

```bash
pip install -r vm-managment-app/requirements.txt
uvicorn app.main:app --app-dir vm-managment-app --reload --host 127.0.0.1 --port 8787
```

Open:

```text
http://127.0.0.1:8787
```

Local bind is `127.0.0.1` only.

## Git prepare flow in UI

Dashboard includes a "Prepare Branch + Commit" panel:

1. Optional branch name (or app default)
2. Optional commit message (or app default)
3. App switches/creates branch, stages only config files, commits
4. App returns next commands for push/PR

Default branch format:

```text
vm-managment-app/config-update-YYYYMMDD-HHMMSS
```

Default commit message:

```text
chore(vm-configs): update config via vm-managment-app
```

## Validation rules enforced

- Required IDs and required fields
- Unique machine/operation IDs (map keys)
- operation.machine references existing machine
- setup references exist in `vm-setups/<setup_id>/stage.yaml`
- SSH fields required for `exec_mode=ssh`
- rules reference valid setup IDs
- JSON object validation for params/defaults fields

## Notes

- This app does not change runtime CLI behavior.
- This app does not push branches or auto-open PRs.
- Runtime still validates via `tools/quick_validate.py` and `runtime/vmcx doctor --ci`.
