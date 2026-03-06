# Install Skill Examples

Prompt:
`install base packages on n8n-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target n8n-vm --stages vm_install`

Run:
`./vm-codex/runtime/vmcx run --target n8n-vm --stages vm_install --confirm`

Prompt:
`install only docker and git on manual-app-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target manual-app-vm --stages vm_install --params '{"vm_install":{"install_only":"docker,git"}}'`

Run:
`./vm-codex/runtime/vmcx run --target manual-app-vm --stages vm_install --params '{"vm_install":{"install_only":"docker,git"}}' --confirm`
