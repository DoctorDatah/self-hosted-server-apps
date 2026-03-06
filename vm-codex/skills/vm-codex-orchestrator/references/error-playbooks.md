# Error Playbooks

## preflight_mismatch

- Cause: missing required file or incompatible target prerequisites.
- Action: fix missing file/config, rerun `plan`, then `run`.

## confirmation_required

- Cause: run command missing explicit confirmation.
- Action: rerun with `--confirm` only after user approval.

## non_retryable_stage_error

- Cause: stage script returned non-zero.
- Action: inspect `vm-codex/local-state/logs/<run_id>.log`, fix issue, then `resume`.

## target_unreachable

- Cause: group run target failed unexpectedly.
- Action: rerun failing target as single-target command for focused recovery.
