---
name: vm-codex-install
description: Run VM installation stages through the local vm-codex runtime with dynamic target/profile handling. Use when user asks to install base packages, toolchains, or host prerequisites on one VM or a VM group.
---

# vm-codex-install

Use this skill for `vm_install` operations only.

## Preconditions

1. Verify `vm-codex/runtime/vmcx` exists.
2. Verify target or group exists via:

```bash
./vm-codex/runtime/vmcx list-targets
./vm-codex/runtime/vmcx list-groups
```

## Plan First

Single target:

```bash
./vm-codex/runtime/vmcx plan --target <target_id> --stages vm_install [--params '<json>']
```

Group:

```bash
./vm-codex/runtime/vmcx run-group --group <group> --stages vm_install --concurrency <n> --dry-run --confirm
```

Use `--params` to override installation selection:

```json
{"vm_install":{"install_only":"docker,git,python"}}
```

## Output Contract Before Apply

Always print:
1. Resolved targets.
2. Resolved stage (`vm_install`).
3. Config and requirements sources.
4. Exact `install_all.sh` command(s).
5. Risk note.
6. Confirmation prompt.

## Apply

Single target:

```bash
./vm-codex/runtime/vmcx run --target <target_id> --stages vm_install [--params '<json>'] --confirm
```

Group:

```bash
./vm-codex/runtime/vmcx run-group --group <group> --stages vm_install --concurrency <n> --confirm
```

## Recovery

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
./vm-codex/runtime/vmcx resume --run-id <run_id>
```

Use `references/examples.md` for common prompts.
