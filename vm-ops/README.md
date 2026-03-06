# vm-ops

`vm-ops` is a stage-first VM operations scaffold for local bootstrap, SSH execution, and thin CI wrappers.

All machine configuration lives under `vm-configs/`:
- `vm-configs/vm-machines.yaml`
- `vm-configs/vm-operations.yaml`
- `vm-configs/vm-env-rules.yaml`

## Quick start

```bash
cd vm-ops
./runtime/vmcx doctor --ci
./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh
./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode local
```

## Notes

- `.yaml` files in this scaffold are JSON-compatible YAML (JSON syntax).
- Runtime state is written to `local-state/runs/`.
- Secrets are resolved at runtime via `tools/infisical_resolve.sh`.
