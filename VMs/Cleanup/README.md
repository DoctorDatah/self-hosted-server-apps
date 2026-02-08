# VM Cleanup

Comprehensive cleanup for a VM (containers, volumes, images, networks, repo folders, and optional package uninstall).

## Run
```bash
sudo -E "/home/malik/self-hosted-server-apps/VMs/cleanup/cleanup_vm.sh"
or
sudo -E "VMs/Cleanup/cleanup_vm.sh"

```

## Behavior
- First prompt: full clean (no further prompts)
- Otherwise, asks yes/no for each cleanup step

## Notes
- Removes `/data/coolify` if you approve that step
- Removes repo folders in `/home/malik` and `/root` if approved
- Uninstalls Docker, Git, and Python3 if approved
