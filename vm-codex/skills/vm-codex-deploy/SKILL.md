---
name: vm-codex-deploy
description: Execute application deployment stages (`app_deploy`) with section-aware control (`infra`, `app`, `post`, `all`) through local vm-codex runtime. Use when user asks for full deploys or sectional app deploys on a VM.
---

# vm-codex-deploy

Use this skill for app deployment only.

## Section Mapping

Allowed sections:
- `infra`
- `app`
- `post`
- `all`

Set section with params:

```json
{"app_deploy":{"section":"app"}}
```

## Plan First

```bash
./vm-codex/runtime/vmcx plan --target <target_id> --stages app_deploy [--params '<json>']
```

## Print Output Contract

Before apply, print:
1. Target.
2. Stage (`app_deploy`) and section.
3. Effective config sources.
4. Exact deploy command(s).
5. Risk note.
6. Confirmation prompt.

## Apply

```bash
./vm-codex/runtime/vmcx run --target <target_id> --stages app_deploy [--params '<json>'] --confirm
```

## Recovery

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
./vm-codex/runtime/vmcx resume --run-id <run_id>
```

Use `references/examples.md` for common sectional deploy flows.
