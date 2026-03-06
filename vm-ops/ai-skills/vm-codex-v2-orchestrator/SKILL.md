# vm-codex-v2-orchestrator

Use this skill to resolve broad VM operation intent into `vmcx` alias/target/stages.

## Workflow

1. Resolve intent to alias or explicit target+stages.
2. Print a plan summary with exact command.
3. Require explicit confirmation for mutating runs.
4. Execute `vmcx run ... --confirm`.
5. Return `run_id` and next commands (`status`, `resume`, `cancel`).
