# APPS_README.MD

## 0. In Plain English (What and Why)
`apps/` is the place where you describe each app in simple config, so the system knows how to handle that app.

What this means in real life:
- If you add a new app, you add one app config here.
- If deploy/backup behavior differs by app, you define it here.

Why this exists:
- Without this folder, every app rule would be hardcoded in scripts.
- That would make changes risky and slow.
- This folder makes app changes safer and easier.

## 0.1 First-Time User Start Here
1. Open `apps/n8n/app.yaml` and read the keys.
2. Match keys to real app behavior (health URL, data path, defaults).
3. Run `python3 tools/quick_validate.py` after any change.
4. Run `./runtime/vmcx plan ...` before `run`.

## 0.2 Common Beginner Mistakes
- Mistake: Using wrong `app_id` string.
  Fix: Keep `app_id` consistent across app config, aliases, and params.
- Mistake: Putting secrets in `app.yaml`.
  Fix: Keep secrets in secret manager references, not plain text config.

## 0.3 Edit vs Do Not Edit
- Edit here when app behavior changes.
- Do not edit here for VM SSH details (that belongs in `vm-configs/vm-machines.yaml`).

## 1. What This Folder Is About
The `apps/` folder is where you describe each application in a way the vm-ops system can understand.

Think of `apps/` as the "application contract" layer:
- `runtime/` knows how to execute operations.
- `vm-setups/` knows how to do install/deploy/backup/restore tasks.
- `apps/` tells the system app-specific details (for example n8n vs coolify).

Without `apps/`, every app detail would need to be hardcoded into stages or commands. This folder keeps app behavior clean and organized.

## 2. What It Holds
Current structure:
- `apps/n8n/app.yaml`
- `apps/coolify/app.yaml`

Each `app.yaml` contains app-level settings such as:
- `app_id`: unique app key used across runtime and stages.
- `default_target_group`: preferred group for this app.
- `deploy_stage_params`: defaults used by deploy stage.
- `backup_stage_params`: defaults used by backup stage.
- `restore_stage_params`: defaults and restrictions for restore.
- `health_checks`: post-deploy checks.
- `artifacts_policy`: what logs/manifests should be retained.

Practical example from current repo:
- `apps/n8n/app.yaml` defines health timeout and backup paths under `/var/lib/n8n`.

## 3. How It Relates to Other Components
- `vm-configs/vm-machines.yaml` chooses machines and connectivity.
- `vm-configs/vm-operations.yaml` maps operation names to machine + setup list.
- `vm-configs/vm-env-rules.yaml` controls what is allowed.
- `runtime/vmcx` merges all that context and executes stages.
- `vm-setups/app_deploy`, `vm-setups/backup_app`, and `vm-setups/restore_app` consume app-specific params.

Simple flow:
1. User runs `./runtime/vmcx run --alias n8n-app-deploy ...`
2. Alias resolves machine/setups from `vm-configs/vm-operations.yaml`
3. Runtime merges profile + alias + CLI params
4. Stage runs with app context from `app.yaml`

## 4. How Users Can Use It and What For
Use `apps/` when you need to onboard a new app or tune app behavior.

### Common tasks
- Add a new app:
  1. Create `apps/<new-app>/app.yaml`
  2. Set `app_id`, defaults, health checks, artifact policy
  3. Add matching operations in `vm-configs/vm-operations.yaml`
  4. Validate with `python3 tools/quick_validate.py`

- Tune deploy defaults:
  - Edit `deploy_stage_params` in app YAML
  - Run:
    - `./runtime/vmcx plan --alias <app-deploy-alias> --exec-mode ssh`
    - `./runtime/vmcx run --alias <app-deploy-alias> --confirm --exec-mode ssh`

- Tune backup/restore behavior:
  - Edit `backup_stage_params` or `restore_stage_params`
  - Validate and test on staging first.

### What not to do
- Do not put secrets here. Use secret refs and runtime resolution.
- Do not put machine SSH data here. That belongs in `vm-configs/vm-machines.yaml`.
- Do not implement shell logic here. That belongs in `vm-setups/`.

### Quick troubleshooting
- If deploy fails due to missing params, check `app.yaml` keys and alias defaults.
- If restore is blocked, check policy and environment restrictions.

## 5. Examples
### Example: Add a new app definition
```bash
mkdir -p apps/myapp
cat > apps/myapp/app.yaml <<'YAML'
{
  "app_id": "myapp",
  "default_target_group": "myapp-stage",
  "deploy_stage_params": {"health_timeout": 120},
  "backup_stage_params": {"backup_paths": ["/var/lib/myapp"]},
  "restore_stage_params": {"allowed_environments": ["stage"]},
  "health_checks": [{"type": "http", "url": "https://myapp.example.com/healthz"}],
  "artifacts_policy": {"retain_logs": true, "retain_manifests": true}
}
YAML
python3 tools/quick_validate.py
```

### Example: Deploy with app alias
```bash
./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh
./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

## 6. Expansion Factor (How This Scales)
When you add more applications, this folder grows linearly: one app folder per app.

Scale pattern:
- Add `apps/<app>/app.yaml` for each new app.
- Keep app-specific defaults here instead of copying logic into stages.
- Reuse shared stage logic (`app_deploy`, `backup_app`, `restore_app`) for every app.

If you add 10+ apps:
- Standardize required keys in every `app.yaml`.
- Keep naming consistent (`app_id`, group names, health endpoints).
- Add operation entries in `vm-configs/vm-operations.yaml` for each app (`<app>-deploy`, `<app>-backup`, etc.).
