---
name: vm-codex-orchestrator
description: Drive end-to-end VM operations using the local vm-codex runtime with plan-first safety and explicit confirmation. Use for high-level requests like "set up this VM", "deploy app stack", "do n8n vm thing", group operations, shorthand alias resolution, and composing install/deploy/cloudflare/backup/restore stages.
---

# vm-codex-orchestrator

Use this skill as the primary entrypoint for VM operations.

## Resolve Workspace

1. Verify the repo root has `vm-codex/runtime/vmcx`.
2. If missing, stop and tell the user exactly how to proceed:
- Run from the repo root that contains `vm-codex`.
- If skills are not installed globally, run `./vm-codex/tools/install_skills.sh`.

## Resolve Intent

1. Attempt alias resolution first:
- Load aliases from `vm-codex/inventory/aliases.yaml`.
- Match exact alias names when provided.
- Use intent hints from `references/alias-intents.md` for shorthand prompts.
2. If alias is not resolved, run a wizard:
- Ask target or group.
- Ask stages bundle or custom stages.
- Ask optional params overrides.
3. Keep stage names explicit:
- `vm_install`
- `app_deploy`
- `cloudflare_vm_access`
- `cloudflare_app_access`
- `backup_app`
- `restore_app`

## Build Plan Command

Use one of:

```bash
./vm-codex/runtime/vmcx plan --alias <alias>
./vm-codex/runtime/vmcx plan --target <target_id> --stages <csv> [--params '<json>']
./vm-codex/runtime/vmcx run-group --group <group> --stages <csv> --concurrency <n> --dry-run --confirm
```

Use `run-group ... --dry-run --confirm` as the plan equivalent for group operations.

## Print Required Skill Output Contract

Before execution, always print:
1. Resolved targets.
2. Resolved stages.
3. Effective config sources.
4. Exact command(s) that will run.
5. Risk notes per stage.
6. Explicit confirmation prompt.

Use the `summary` returned by `vmcx` as source of truth.

## Execute Only After Explicit Confirmation

Single target:

```bash
./vm-codex/runtime/vmcx run --alias <alias> --confirm
./vm-codex/runtime/vmcx run --target <target_id> --stages <csv> [--params '<json>'] --confirm
```

Group:

```bash
./vm-codex/runtime/vmcx run-group --group <group> --stages <csv> --concurrency <n> --confirm
```

## Composition Modes

1. Direct stage mode: execute one stage only.
2. Alias bundle mode: execute predefined multi-stage bundles.
3. Group mode: execute same stages across label/group targets.
4. Delegation mode: if user asks specifically for install/deploy/cloudflare/backup-restore, route to the corresponding stage skill.

## Variable Resolution

Treat effective config precedence as:
1. base profile
2. role overlay
3. target overlay
4. alias defaults
5. explicit CLI/skill overrides

## Resume/Cancel/Status

Use:

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
./vm-codex/runtime/vmcx resume --run-id <run_id>
./vm-codex/runtime/vmcx cancel --run-id <run_id>
```

## References

- Use `references/examples.md` for prompt-to-command examples.
- Use `references/alias-intents.md` for shorthand parsing.
- Use `references/error-playbooks.md` for recovery flow.
