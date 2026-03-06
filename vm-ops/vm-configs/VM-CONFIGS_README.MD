# VM-CONFIGS_README.MD

## 1. What This Folder Is About
`vm-configs/` is the simplified config center for vm-ops.

Lite mode uses only 3 active config files:
- `vm-machines.yaml`
- `vm-operations.yaml`
- `vm-env-rules.yaml`

This keeps setup easier for humans and reduces cross-file confusion.

## 2. What It Holds
Active files:
- `vm-configs/vm-machines.yaml`
  - machine definitions, groups, SSH info, enabled setups, default params
- `vm-configs/vm-operations.yaml`
  - human-friendly operation names mapped to machine + setup list + params
- `vm-configs/vm-env-rules.yaml`
  - policy guardrails (what is allowed in which env)

## 3. How It Relates to Other Components
- `runtime/vmcx` reads these 3 files for all `plan/run/list/doctor` commands.
- `ai-skills/` should map intent to operations defined in `vm-operations.yaml`.
- `vm-setups/` are the executable units referenced by machines/operations.
- CI workflows call runtime, so they automatically use the same 3-file config.

## 4. How Users Can Use It and What For
Most common edits:
1. Add a machine: edit `vm-configs/vm-machines.yaml`
2. Add an operation alias: edit `vm-configs/vm-operations.yaml`
3. Add/adjust safety rule: edit `vm-configs/vm-env-rules.yaml`

After edits:
```bash
cd vm-ops
python3 tools/quick_validate.py
./runtime/vmcx doctor --ci
./runtime/vmcx plan --alias <operation-name> --exec-mode <local|ssh|auto>
```
