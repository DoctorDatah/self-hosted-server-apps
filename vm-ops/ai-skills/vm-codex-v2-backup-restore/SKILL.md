# vm-codex-v2-backup-restore

Handles backup and restore operations with policy-aware routing.

## Examples

```bash
./runtime/vmcx run --alias n8n-app-backup --confirm --exec-mode ssh
./runtime/vmcx run --alias n8n-app-restore-staging --params '{"backup_id":"bkp-2026-03-06-001"}' --confirm --exec-mode ssh
```
