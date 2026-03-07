# vm-ops

`vm-ops` is a stage-first VM operations scaffold for local bootstrap, SSH execution, and thin CI wrappers.

All machine configuration lives under `vm-configs/`:
- `vm-configs/vm-machines.yaml`
- Optional legacy files:
  - `vm-configs/vm-operations.yaml`
  - `vm-configs/vm-env-rules.yaml`

Primary config is machine-first:
- per-machine setup allow-list: `enabled_setups`
- per-machine operation sets: `set_of_operations`

## Quick start

```bash
cd vm-ops
./runtime/vmcx doctor --ci
./runtime/vmcx plan --target n8n-stage-1 --stages vm_install --exec-mode local
./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local
```

## Notes

- `.yaml` files in this scaffold are JSON-compatible YAML (JSON syntax).
- Runtime state is written to `local-state/runs/`.
- Secrets are resolved at runtime via `tools/infisical_resolve.sh`.
