# TOOLS_README.MD

## 0. In Plain English (What and Why)
`tools/` contains helper scripts that support operations.

What this means in real life:
- Use these scripts for validation, repo prep, and secret resolution.
- They are utilities, not the main orchestration engine.

Why this exists:
- Keeps helper logic separate from runtime core and stage logic.
- Makes common support tasks reusable in local and CI contexts.

## 0.1 First-Time User Start Here
1. Run `python3 tools/quick_validate.py`.
2. Read usage comments in each script before executing.
3. Use `ensure_repo.sh` when repo presence/update is needed.

## 0.2 Common Beginner Mistakes
- Mistake: Using tools to replace stage logic.
  Fix: Keep operations in `vm-setups/`; tools should assist.
- Mistake: Running secret resolver without required env or CLI setup.
  Fix: configure env/Infisical access first.

## 0.3 Edit vs Do Not Edit
- Edit tools for cross-cutting helper improvements.
- Do not put business-critical deploy logic here.

## 1. What This Folder Is About
The `tools/` folder contains support utilities used by runtime, operators, and CI.

These scripts help with validation, repo prep, secret resolution, and skill installation.

## 2. What It Holds
Current scripts:
- `tools/quick_validate.py`: fast project validation wrapper
- `tools/ensure_repo.sh`: clone/update repo at a target path
- `tools/infisical_resolve.sh`: resolve secret refs at runtime
- `tools/install_skills.sh`: copy skills into Codex skills location

## 3. How It Relates to Other Components
- `quick_validate.py` invokes `runtime/vmcx doctor --ci`.
- `repo_clone_or_update` stage can call `ensure_repo.sh`.
- SSH executor secret path can call `infisical_resolve.sh`.
- Operator workflow setup can use `install_skills.sh`.

## 4. How Users Can Use It and What For
Use these scripts as operational helpers.

### Quick validate
- Command:
  - `python3 tools/quick_validate.py`
- Purpose:
  - fast sanity check before execution or CI.

### Ensure repo
- Command:
  - `bash tools/ensure_repo.sh <repo_url> <repo_path> [branch]`
- Purpose:
  - guarantee remote/local target has expected repo branch.

### Resolve secret
- Command:
  - `bash tools/infisical_resolve.sh infisical://<project>/<path>`
- Purpose:
  - fetch secret value at runtime (or fail clearly).

### Install skills
- Command:
  - `bash tools/install_skills.sh`
- Purpose:
  - copy vm-ops skills into `$CODEX_HOME/skills` (or default Codex home).

### Best practices
- Keep tools generic and reusable.
- Avoid adding stage mutation logic here.
- Prefer runtime+stage contracts for operational behavior.

## 5. Examples
### Example: Ensure remote repo exists before SSH stage run
```bash
bash tools/ensure_repo.sh https://github.com/DoctorDatah/self-hosted-server-apps.git /repo/vm-ops main
```

### Example: Resolve a secret reference
```bash
bash tools/infisical_resolve.sh infisical://vm-codex/ssh/n8n-prod-1
```

### Example: Quick preflight
```bash
python3 tools/quick_validate.py
```

## 6. Expansion Factor (How This Scales)
Tools scale operational support without bloating runtime or stage logic.

Scale pattern:
- Add helper scripts only for cross-cutting support tasks.
- Keep tool scripts composable and side-effect clear.
- Use tools to assist runtime/stages, not replace them.

If you add more environments:
- Expand validation and helper coverage first.
- Keep secret and repo helpers environment-agnostic.
- Document each new tool with expected inputs/outputs.
