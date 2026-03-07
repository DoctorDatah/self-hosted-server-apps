# VM-CONFIGS_README.MD

## 1. What This Folder Is About
`vm-configs/` is the simplified config center for vm-ops.

Primary active file:
- `vm-machines.yaml`

Optional legacy files:
- `vm-operations.yaml`
- `vm-env-rules.yaml`

## 2. What It Holds
Active files:
- `vm-configs/vm-machines.yaml`
  - machine definitions, groups, SSH info, enabled setups, set_of_operations, default params
- Optional:
  - `vm-configs/vm-operations.yaml` (legacy alias file)
  - `vm-configs/vm-env-rules.yaml` (legacy env rules file)

## 3. How It Relates to Other Components
- `runtime/vmcx` reads machine config directly and can derive aliases from machine `set_of_operations`.
- `ai-skills/` should map intent to machine operation sets (or optional legacy aliases).
- `vm-setups/` are the executable units referenced by machine setup lists.
- CI workflows call runtime, so they automatically use the same machine-first config.

## 4. How Users Can Use It and What For
Most common edits:
1. Add a machine: edit `vm-configs/vm-machines.yaml`
2. Add per-machine operation set: edit `machines.<id>.set_of_operations` in `vm-machines.yaml`
3. (Optional) keep legacy aliases/rules files if you still need them

After edits:
```bash
cd vm-ops
python3 tools/quick_validate.py
./runtime/vmcx doctor --ci
./runtime/vmcx list-aliases
./runtime/vmcx plan --alias <machine-set-alias> --exec-mode <local|ssh|auto>
```
