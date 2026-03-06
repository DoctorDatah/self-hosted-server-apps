# VM Codex User Guide (Goal-Focused, Skills-First)

This guide is for the new `vm-codex` model only.
No API stack is included; all operations run through local `vmcx` + skills.

## 1) What problem this solves for you

You have multiple machines with different jobs:
- Proxmox host tasks (`vm_install` and host prep)
- App VM tasks (install + app deploy + Cloudflare)
- Future VMs with different requirements
- Backup and staging restore workflows

You need one consistent way to operate all of them without rewriting scripts every time.

`vm-codex` gives that by combining:
- inventory (`targets.yaml`) for variable machine count
- layered config for variable requirements
- alias shortcuts for fast repeat workflows
- local runtime (`vmcx`) with plan-first and explicit confirm
- Codex skills as the primary interface

## 2) Mental model (simple)

1. You say what you want: `do n8n vm setup`.
2. Skill resolves alias/target/stages.
3. Skill runs a plan command first.
4. You review exact commands + risk.
5. You confirm.
6. Skill runs apply.
7. State/logs are written locally for resume/debug.

No API is required for the normal workflow.

## 3) Where to run this

Run `vmcx` on the machine where execution should happen.

Examples:
- Proxmox host work: run from repo clone on Proxmox host.
- App VM work: run from repo clone on that app VM.
- Group operations: run from a machine that can execute those target-local scripts in your setup model.

## 4) One-time setup on each machine

From repo root:

```bash
cd /Users/hassan/self-hosted-server-apps
python3 -m pip install --user pyyaml
chmod +x ./vm-codex/runtime/vmcx
chmod +x ./vm-codex/runtime/stages/*.sh
chmod +x ./vm-codex/installation/install_all.sh
```

Optional but recommended: install skills into your Codex home.

```bash
./vm-codex/tools/install_skills.sh
```

Verify runtime visibility:

```bash
./vm-codex/runtime/vmcx list-targets
./vm-codex/runtime/vmcx list-groups
./vm-codex/runtime/vmcx list-aliases
```

## 5) Fastest way to operate day-to-day

### A) Full n8n VM setup

Plan:

```bash
./vm-codex/runtime/vmcx plan --alias n8n-vm-setup
```

Apply:

```bash
./vm-codex/runtime/vmcx run --alias n8n-vm-setup --confirm
```

### B) Deploy only app section on manual app VM

Plan:

```bash
./vm-codex/runtime/vmcx plan \
  --target manual-app-vm \
  --stages app_deploy \
  --params '{"app_deploy":{"section":"app"}}'
```

Apply:

```bash
./vm-codex/runtime/vmcx run \
  --target manual-app-vm \
  --stages app_deploy \
  --params '{"app_deploy":{"section":"app"}}' \
  --confirm
```

### C) Install base packages on all app-tier VMs

Plan-equivalent:

```bash
./vm-codex/runtime/vmcx run-group \
  --group app-tier \
  --stages vm_install \
  --concurrency 2 \
  --dry-run --confirm
```

Apply:

```bash
./vm-codex/runtime/vmcx run-group \
  --group app-tier \
  --stages vm_install \
  --concurrency 2 \
  --confirm
```

### D) Restore latest backup for n8n to staging

Plan:

```bash
./vm-codex/runtime/vmcx plan --alias restore-n8n-staging
```

Apply:

```bash
./vm-codex/runtime/vmcx run --alias restore-n8n-staging --confirm
```

## 6) How variable behavior is handled

The same stage adapts by layered resolution precedence:
1. base profile
2. role overlay
3. target overlay
4. alias defaults
5. explicit command overrides

So one `vm_install` stage can behave differently for Proxmox host vs app VM without new scripts.

## 7) How to add a new VM cleanly

1. Add target to `vm-codex/inventory/targets.yaml` with labels and enabled stages.
2. Add overlay: `vm-codex/profiles/overlays/<target-or-role>.yaml` if needed.
3. Add target requirements: `vm-codex/requirements/targets/<target_id>.yaml` if needed.
4. Optionally add shortcut alias in `vm-codex/inventory/aliases.yaml`.
5. Run a plan command for first validation.

## 8) How to use skills (your preferred interface)

You have both:
- One giant skill: `vm-codex-orchestrator`
- Composable stage skills:
  - `vm-codex-install`
  - `vm-codex-deploy`
  - `vm-codex-cloudflare`
  - `vm-codex-backup-restore`

Typical usage pattern:
- Use orchestrator for fuzzy/high-level asks.
- Use stage skills for precise, single-purpose operations.

## 9) Run tracking and recovery

Check run state:

```bash
./vm-codex/runtime/vmcx status --run-id <run_id>
```

Resume failed/canceled run:

```bash
./vm-codex/runtime/vmcx resume --run-id <run_id>
```

Cancel active run:

```bash
./vm-codex/runtime/vmcx cancel --run-id <run_id>
```

Logs:
- `vm-codex/local-state/logs/<run_id>.log`

Run records:
- `vm-codex/local-state/runs/<run_id>.json`

## 10) Important guardrails

- Never skip planning on first execution of a changed config.
- Always require explicit `--confirm` before mutation.
- `restore_app` is staging-only by design.
- Group runs use bounded concurrency and summarize failures per target.

## 11) Common “what do I type?” prompts

- `do n8n vm thingy`
- `deploy only app layer on manual-app-vm`
- `install base packages for all app VMs`
- `restore latest backup for n8n to staging`

These map directly to commands shown above through aliases or wizard resolution in the orchestrator skill.
