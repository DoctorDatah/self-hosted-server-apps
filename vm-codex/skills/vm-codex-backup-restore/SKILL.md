---
name: vm-codex-backup-restore
description: Run backup and restore stages for application data using the local vm-codex runtime, including staging-only restore guardrails. Use when user asks to create backups, verify artifacts, or restore app data safely.
---

# vm-codex-backup-restore

Use this skill for `backup_app` and `restore_app` stages.

## Guardrails

1. Always plan first.
2. Require explicit confirmation before apply.
3. Enforce restore target type `staging`.

## Backup Flow

Plan:

```bash
./vm-codex/runtime/vmcx plan --target <target_id> --stages backup_app
```

Apply:

```bash
./vm-codex/runtime/vmcx run --target <target_id> --stages backup_app --confirm
```

## Restore Flow

Use staging param:

```json
{"restore_app":{"restore_target_type":"staging"}}
```

Plan:

```bash
./vm-codex/runtime/vmcx plan --target <target_id> --stages restore_app --params '{"restore_app":{"restore_target_type":"staging"}}'
```

Apply:

```bash
./vm-codex/runtime/vmcx run --target <target_id> --stages restore_app --params '{"restore_app":{"restore_target_type":"staging"}}' --confirm
```

## Output Contract Before Apply

Always print:
1. Target.
2. Stage(s).
3. Config source list.
4. Exact backup/restore commands.
5. High-risk note.
6. Confirmation prompt.

## Recovery

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
./vm-codex/runtime/vmcx resume --run-id <run_id>
```

Use `references/examples.md` for common operations.
