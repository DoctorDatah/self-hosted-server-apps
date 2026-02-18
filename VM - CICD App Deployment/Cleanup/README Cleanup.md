# VM Cleanup

Comprehensive cleanup for a VM (containers, volumes, images, networks, repo folders, and data dirs).

## Run
```bash
sudo -E "/home/malik/self-hosted-server-apps/VM - CICD App Deployment/cleanup/cleanup_vm.sh"
or
sudo -E "VM - CICD App Deployment/Cleanup/cleanup_vm.sh"

```

## Behavior
- First prompt: full clean (no further prompts)
- Otherwise, asks yes/no for each cleanup step

## Notes
- Removes `/data/coolify` if you approve that step
- Removes repo folders in `/home/malik` and `/root` if approved
