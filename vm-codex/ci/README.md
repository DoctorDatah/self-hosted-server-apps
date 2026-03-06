# vm-codex CI Contracts

CI is validation-only for the skills-first local runtime.

All vm-codex workflows must:
- Validate shell scripts (`bash -n`)
- Run runtime unit tests
- Run `vmcx` smoke commands (`list-*`, `plan`)
- Validate all skills with `vm-codex/tools/quick_validate.py`
- Never call a remote API service for operations execution
