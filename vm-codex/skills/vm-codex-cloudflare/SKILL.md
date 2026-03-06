---
name: vm-codex-cloudflare
description: Configure Cloudflare connectivity stages for VM access and app access using local vm-codex runtime. Use when user asks to set up or update Cloudflare tunnel/access layers for a target VM.
---

# vm-codex-cloudflare

Use this skill for Cloudflare stage execution.

## Stage Selection

- VM access only: `cloudflare_vm_access`
- App access only: `cloudflare_app_access`
- Both: `cloudflare_vm_access,cloudflare_app_access`

## Plan First

```bash
./vm-codex/runtime/vmcx plan --target <target_id> --stages <csv>
```

## Output Contract Before Apply

Always print:
1. Target.
2. Selected cloudflare stage(s).
3. Config source list.
4. Exact cloudflare command(s).
5. Risk note.
6. Confirmation prompt.

## Apply

```bash
./vm-codex/runtime/vmcx run --target <target_id> --stages <csv> --confirm
```

## Recovery

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
./vm-codex/runtime/vmcx resume --run-id <run_id>
```

Use `references/examples.md` for quick prompts.
