# vm-v1

`vm-v1` is a stage-first VM operations scaffold for local bootstrap, SSH execution, and thin CI wrappers.

## Quick start

```bash
cd vm-v1
./runtime/vmcx doctor --ci
./runtime/vmcx plan --alias n8n-app-deploy --exec-mode ssh
./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode local
```

## Notes

- `.yaml` files in this scaffold are JSON-compatible YAML (JSON syntax).
- Runtime state is written to `local-state/runs/`.
- Secrets are resolved at runtime via `tools/infisical_resolve.sh`.
