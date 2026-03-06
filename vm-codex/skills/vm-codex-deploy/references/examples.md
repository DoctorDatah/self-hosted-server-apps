# Deploy Skill Examples

Prompt:
`deploy app layer on manual-app-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target manual-app-vm --stages app_deploy --params '{"app_deploy":{"section":"app"}}'`

Run:
`./vm-codex/runtime/vmcx run --target manual-app-vm --stages app_deploy --params '{"app_deploy":{"section":"app"}}' --confirm`

Prompt:
`do full deploy on n8n-vm`

Plan:
`./vm-codex/runtime/vmcx plan --target n8n-vm --stages app_deploy --params '{"app_deploy":{"section":"all"}}'`

Run:
`./vm-codex/runtime/vmcx run --target n8n-vm --stages app_deploy --params '{"app_deploy":{"section":"all"}}' --confirm`
