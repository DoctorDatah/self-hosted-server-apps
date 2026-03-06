# Examples Catalog

## Example 1: Full n8n VM setup shortcut

Prompt:
`do n8n vm thingy`

Resolution:
- Alias: `n8n-vm-setup`
- Target: `n8n-vm`
- Stages: `vm_install,app_deploy,cloudflare_vm_access,cloudflare_app_access`

Plan command:
`./vm-codex/runtime/vmcx plan --alias n8n-vm-setup`

Run command:
`./vm-codex/runtime/vmcx run --alias n8n-vm-setup --confirm`

Outcomes:
- Success: all stages complete.
- Preflight fail: no mutation, fix missing dependency/file and re-run.
- Stage fail: run fails fast, then `status` and `resume`.

## Example 2: Deploy only app section

Prompt:
`deploy only app layer on manual-app-vm`

Resolved params:
`{"app_deploy":{"section":"app"}}`

Plan command:
`./vm-codex/runtime/vmcx plan --target manual-app-vm --stages app_deploy --params '{"app_deploy":{"section":"app"}}'`

Run command:
`./vm-codex/runtime/vmcx run --target manual-app-vm --stages app_deploy --params '{"app_deploy":{"section":"app"}}' --confirm`

Variable behavior:
- `section=infra` changes command set.
- `section=all` runs pull + up + ps path.

## Example 3: Install base packages for all app VMs

Prompt:
`install base packages for all app VMs`

Resolved target selector:
- Group: `app-tier`

Plan-equivalent command:
`./vm-codex/runtime/vmcx run-group --group app-tier --stages vm_install --concurrency 2 --dry-run --confirm`

Run command:
`./vm-codex/runtime/vmcx run-group --group app-tier --stages vm_install --concurrency 2 --confirm`

Outcome:
- Continue-on-failure summary per target.

## Example 4: Staging restore only

Prompt:
`restore latest backup for n8n to staging`

Alias:
`restore-n8n-staging`

Plan command:
`./vm-codex/runtime/vmcx plan --alias restore-n8n-staging`

Run command:
`./vm-codex/runtime/vmcx run --alias restore-n8n-staging --confirm`

Guardrail:
- Blocked if `restore_target_type` is not `staging`.
