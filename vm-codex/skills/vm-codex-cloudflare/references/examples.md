# Cloudflare Skill Examples

Prompt:
`set up cloudflare vm access on n8n-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target n8n-vm --stages cloudflare_vm_access`

Run:
`./vm-codex/runtime/vmcx run --target n8n-vm --stages cloudflare_vm_access --confirm`

Prompt:
`configure both cloudflare layers on manual-app-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target manual-app-vm --stages cloudflare_vm_access,cloudflare_app_access`

Run:
`./vm-codex/runtime/vmcx run --target manual-app-vm --stages cloudflare_vm_access,cloudflare_app_access --confirm`
