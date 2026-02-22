# VM Cleanup

Comprehensive cleanup for a VM (containers, volumes, images, networks, repo folders, and data dirs).

## Run
```bash

chmod +x "/root/self-hosted-server-apps/Home Server Setup/Cleanup/cleanup_vm.sh"

"/root/self-hosted-server-apps/Home Server Setup/Cleanup/cleanup_vm.sh"
```

## Behavior
- First prompt: full clean (no further prompts)
- Otherwise, asks yes/no for each cleanup step

## Notes
- Removes `/data/coolify` if you approve that step
- Uninstalls the OpenAI Codex CLI (`@openai/codex`) if you approve that step
- Removes `nodejs` and `npm` if you approve that step
- Removes repo folders in `/home/malik` and `/root` if approved
