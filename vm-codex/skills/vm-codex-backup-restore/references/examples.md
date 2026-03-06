# Backup Restore Skill Examples

Prompt:
`backup n8n-vm now`

Plan:
`./vm-codex/runtime/vmcx plan --target n8n-vm --stages backup_app`

Run:
`./vm-codex/runtime/vmcx run --target n8n-vm --stages backup_app --confirm`

Prompt:
`restore latest backup for n8n to staging`

Plan:
`./vm-codex/runtime/vmcx plan --alias restore-n8n-staging`

Run:
`./vm-codex/runtime/vmcx run --alias restore-n8n-staging --confirm`
