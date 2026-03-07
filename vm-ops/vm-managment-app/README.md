# VM Management

`vm-managment-app` is the on-disk folder name. The product/UI name is **VM Management**.

## Purpose

VM Management is a local-first web UI for editing:

- `vm-configs/vm-machines.yaml`
- `vm-configs/vm-operations.yaml`
- `vm-configs/vm-env-rules.yaml`

These files remain source of truth.

## Feature-Isolated Structure

```text
app/
  core/
    app_meta.py
    realtime_bus.py
    file_watch.py
    dependency_graph.py
  features/
    ui_system/
      routes.py
      service.py
      templates/
      static/
    config_management/
      routes_ui.py
      routes_api.py
      services/
        backups.py
        config_store.py
        validators.py
        integrity.py
        cascade.py
      templates/
      static/
  shared/
    schemas.py
    responses.py
```

## Key Behaviors

- Config forms with validation + diff preview.
- Dedicated Branch and Commit feature page lets you manage a UI target branch, commit on demand, and push from UI.
  - Default branch pattern: `config_update/update-YYYYMMDD-HHMMSS`
  - Reuses an existing related branch by default; creates new branch only when none exists
  - Branch operations do not switch your main local checked-out branch
- Referential-integrity-aware delete flow:
  - Analyze dependencies first
  - Explicit cascade confirmation when required
  - Apply via atomic writes only after validation
- Real-time config updates:
  - File watch + SSE (`/api/realtime/config-events`)
  - Stale-data warning and refresh behavior
- Config backup and restore:
  - Create timestamped snapshots with label + remark
  - Stored under `vm-configs/config-backups/` (git-trackable)
  - Filter backups by label/search, exact date, date range, and quick last-N views
  - Delete backups directly from the UI
  - Restore any backup directly back into `vm-configs/*.yaml`
  - Top status shows whether current config is backed up, last backup date, and last restore source
- Settings:
  - Global app settings available from main menu
  - Timezone selection is saved in app data and reused across UI timestamps and default branch naming
  - Full timezone list is available for selection
  - UI target branch preference is saved and reused by commit/push actions
  - Settings file path: `vm-managment-app/app-data/settings.json`

## Run

From `vm-ops/`:

```bash
source vm-managment-app/.venv/bin/activate
uvicorn app.main:app --app-dir vm-managment-app --reload --host 127.0.0.1 --port 8787
```

Open locally:

```text
http://127.0.0.1:8787
```

For remote VM access, see `SPINUP-GUIDE-README.md`.
