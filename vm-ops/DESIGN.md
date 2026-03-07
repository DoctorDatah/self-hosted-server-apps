> NOTE (March 6, 2026): Active runtime uses the Lite config model.
> Source of truth is:
> `vm-configs/vm-machines.yaml` (machine-first), with optional legacy files
> `vm-configs/vm-operations.yaml` and `vm-configs/vm-env-rules.yaml`.
> No legacy fallback folders are used.

Below is the **fully updated, comprehensive plan** for **`vm-codex-v2`**, now expanded to include:

* all the existing architectural information
* the cleaned repository model
* the updated stage-first structure
* the CI role update
* the operating model
* folder-by-folder explanations
* contracts and responsibilities
* rollout phases
* testing
* security
* **use cases**
* **worked examples**
* **operator examples**
* **skill examples**
* **CLI examples**
* **GitHub Actions examples**

I am treating the examples as part of the guide itself, so this is written as both a **design plan** and a **practical operating guide**.

---

# VM-Codex-V2 Comprehensive Updated Plan

## Skills-First VM Operations with Manual Bootstrap, Shared Stages, SSH Execution, and Thin CI/CD Automation

---

# 1. Executive Summary

`vm-codex-v2` is a **greenfield, repo-based VM operations system** designed around the way VM work actually happens in practice.

It is built for a workflow where:

1. a VM is often prepared **manually from inside the machine first**
2. repeated operations are standardized into **shared stage implementations**
3. later, once the VM is ready, the same operations can be run over **SSH**
4. GitHub Actions provides a **thin automation layer**, not a second orchestrator
5. everything remains **local-first, API-free, and runtime-centered**

This system is intentionally **not** a control plane, **not** a long-running service, and **not** an API-driven orchestration platform.

It is a **versioned operations repo** with one execution engine and one stage system that can be invoked from multiple interfaces.

---

# 2. Design Goal

The goal of `vm-codex-v2` is to create a clean and scalable system for:

* bootstrapping VMs
* preparing VM environments
* configuring access
* deploying applications
* cleaning up experimental state
* backing up application state
* restoring state safely
* doing all of the above consistently across:

  * manual local execution
  * remote SSH execution
  * CI/CD execution

The system must support **real operator behavior**, not an idealized one.

That means it must support:

* uncertain initial VM state
* local experimentation
* manual recovery
* gradual transition to automation
* repeatable operations once machines are stable

---

# 3. Core Principles

## 3.1 Manual bootstrap comes first

Many VMs are not SSH-ready at the beginning. They may have:

* weak SSH defaults
* missing users or key auth
* missing packages
* inconsistent shared_vm_config config
* no trusted repo path
* missing Docker or other runtime tools

So the first valid mode is **local inside the VM**.

That is a deliberate design choice.

---

## 3.2 One runtime, many entrypoints

The same runtime should be callable from:

* a skill
* an operator CLI session
* a GitHub Action

This means there is one orchestration engine and one stage implementation layer.

---

## 3.3 All operational logic lives in stages

The actual install, Cloudflare, deploy, backup, restore, and cleanup logic belongs in **stage folders**.

Not in:

* skills
* GitHub workflows
* random support scripts
* ad hoc wrappers

This is the most important maintainability rule in the whole design.

---

## 3.4 CI is validation and remote execution, not orchestration

GitHub Actions should:

* validate
* resolve secrets
* prepare SSH
* call the runtime
* upload logs/artifacts

GitHub Actions should **not** implement install, deploy, backup, or restore logic directly.

---

## 3.5 Secrets are runtime-resolved

Secrets should be resolved from **Infisical** at runtime.

Config files should contain references only, never raw secrets.

---

## 3.6 Local policy is the guardrail layer

The system should not depend on an external policy service.

A local, versioned policy file is sufficient for the initial design.

---

# 4. Final Architectural Decisions

| Area                   | Decision                                                                      |
| ---------------------- | ----------------------------------------------------------------------------- |
| Project style          | Domain-oriented repo with stage-first execution layout                        |
| Stage structure        | Independent folders under top-level `vm-setups/`                                 |
| Runtime design         | One CLI engine (`vmcx`) with local and SSH executors                          |
| Secrets                | Infisical-first                                                               |
| Multi-VM orchestration | Hybrid local + SSH                                                            |
| CI role                | Validation first, then SSH execution for install, deploy, backup, and restore |
| Policy model           | Local static policy file                                                      |
| Operator UX            | Skills-first, with CLI and GitHub Actions using same runtime                  |
| Bootstrap model        | Manual-first, remote later                                                    |
| Control plane          | None                                                                          |
| API requirement        | None                                                                          |

---

# 5. Final Clean Repository Structure

```text
vm-codex-v2/
├─ README.md
├─ USER_GUIDE.md
│
├─ ai-skills/
│  ├─ vm-codex-v2-orchestrator/
│  ├─ vm-codex-v2-install/
│  ├─ vm-codex-v2-cloudflare/
│  ├─ vm-codex-v2-deploy/
│  ├─ vm-codex-v2-cleanup/
│  └─ vm-codex-v2-backup-restore/
│
├─ runtime/
│  ├─ vmcx
│  ├─ lib/
│  ├─ executors/
│  ├─ planner/
│  └─ tests/
│
├─ vm-setups/
│  ├─ repo_clone_or_update/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ templates/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ vm_install/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ templates/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ cloudflare_vm_access/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ templates/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ cloudflare_app_access/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ templates/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ app_deploy/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ templates/
│  │  ├─ adapters/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ cleanup_vm/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  ├─ backup_app/
│  │  ├─ stage.sh
│  │  ├─ stage.yaml
│  │  ├─ scripts/
│  │  ├─ manifests/
│  │  ├─ tests/
│  │  └─ README.md
│  │
│  └─ restore_app/
│     ├─ stage.sh
│     ├─ stage.yaml
│     ├─ scripts/
│     ├─ manifests/
│     ├─ tests/
│     └─ README.md
│
├─ apps/
│  ├─ n8n/
│  │  └─ app.yaml
│  └─ coolify/
│     └─ app.yaml
│
├─ vm-configs/vm-groups/
│  ├─ vm-machines.yaml
│  ├─ vm-set-of-setups.yaml
│  └─ vm-group.yaml
│
├─ vm-configs/vm-profiles/
│  ├─ shared_vm_config/
│  │  └─ default.yaml
│  └─ specifc_vm_config/
│     └─ *.yaml
│
├─ vm-configs/requirements/
│  ├─ global.yaml
│  ├─ roles/
│  └─ targets/
│
├─ vm-configs/vm-env-rules/
│  └─ local-policy.yaml
│
├─ tools/
│  ├─ install_skills.sh
│  ├─ quick_validate.py
│  ├─ infisical_resolve.sh
│  └─ ensure_repo.sh
│
├─ local-state/              # runtime-created, gitignored
│
└─ .github/
   └─ workflows/
      ├─ vm-repo-validate.yml
      ├─ _vm-codex-v2-execute.yml
      ├─ install-n8n-vm.yml
      ├─ deploy-n8n-prod.yml
      ├─ backup-n8n-prod.yml
      ├─ restore-n8n-staging.yml
      └─ additional thin wrappers...
```

---

# 6. What Each Top-Level Folder Is, What It Does, and Why It Exists

## 6.1 `ai-skills/`

### What it is

The human-facing operator UX layer.

### What it does

Skills translate natural-language or semi-structured operator intent into:

* aliases
* targets
* stage lists
* params
* risk notes
* exact runtime commands

### Why it exists

Operators should not have to remember:

* exact target IDs
* exact stage names
* exact merge rules
* exact CLI syntax

Skills provide a clean operator experience while keeping the runtime unchanged.

### Example use case

Operator says:

> “do n8n vm thingy”

The skill resolves that into something like:

* alias: `n8n-vm-install`
* target: `n8n-stage-1`
* stages: `repo_clone_or_update,vm_install,cloudflare_vm_access`
* exec mode: `local` or `ssh`

Then prints a plan before asking for confirmation.

---

## 6.2 `runtime/`

### What it is

The orchestration engine.

### What it does

The runtime is responsible for:

* parsing CLI commands
* loading inventory and config
* resolving targets, groups, and aliases
* merging vm-profiles and params
* checking policies
* selecting an executor
* producing execution plans
* tracking run state
* redacting secrets
* invoking stages

### Why it exists

Without a central runtime, orchestration logic would be spread across:

* skills
* stage scripts
* CI workflows
* helper tools

That would cause drift and make the system hard to reason about.

### Example use case

A GitHub Action passes:

```bash
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

The runtime determines:

* which target this means
* which stages this alias maps to
* what profile specifc_vm_config apply
* whether deploy is allowed in that environment
* which SSH settings to use
* how to record and report the run

---

## 6.3 `vm-setups/`

### What it is

The actual operational implementation layer.

### What it does

Each stage folder contains everything needed for one operational unit:

* the stage entrypoint
* metadata
* scripts
* templates
* tests
* docs
* specialized helper assets

### Why it exists

Your install, deploy, Cloudflare, cleanup, backup, and restore logic are not tiny one-off scripts. They are operational domains. Each one needs room to grow.

This is why `vm-setups/` exists as a first-class top-level folder instead of keeping flat shell scripts under `runtime/vm-setups/`.

### Example use case

The `vm_install` stage may need:

* package installation logic
* Docker installation logic
* system setup templates
* idempotency checks
* role-specific install variants

That belongs in its own folder.

---

## 6.4 `apps/`

### What it is

Per-application configuration.

### What it does

Defines app-specific behavior such as:

* default target group
* deployment parameters
* backup parameters
* restore parameters
* health checks
* artifact expectations

### Why it exists

The runtime should remain generic. App-specific details belong in app definitions.

### Example use case

`apps/n8n/app.yaml` can define:

* the default group for n8n VMs
* health check URLs or commands
* backup paths
* restore validation rules

---

## 6.5 `vm-configs/vm-groups/`

### What it is

The infrastructure map.

### What it does

Defines:

* actual targets
* target groups
* human-friendly aliases

### Why it exists

The runtime needs a structured way to know:

* what machines exist
* how they are grouped
* what friendly operation names mean

### Example use case

Instead of typing a full target and stage list every time, an operator can use:

```bash
vmcx run --alias backup-n8n-prod --confirm
```

which is resolved from `vm-configs/vm-groups/vm-set-of-setups.yaml`.

---

## 6.6 `vm-configs/vm-profiles/`

### What it is

Reusable configuration layers.

### What it does

Defines shared_vm_config settings and specifc_vm_config that are merged into target config.

### Why it exists

Many targets share common patterns, and you do not want to duplicate those settings in every target entry.

### Example use case

A shared_vm_config profile might define:

* logging defaults
* package management behavior
* default runtime assumptions

A role overlay might define:

* Docker install required
* app host-specific packages
* backup behavior

A target overlay might define:

* one host’s custom repo path
* one host’s app-specific override

---

## 6.7 `vm-configs/requirements/`

### What it is

Declarative readiness and capability expectations.

### What it does

Describes what should exist globally, by role, or by target.

### Why it exists

Profiles describe config. Requirements describe readiness expectations.

### Example use case

A role requirement might say an app VM must have:

* Docker
* git
* compose support
* writable app data directory

This can be used by validation and `doctor`.

---

## 6.8 `vm-configs/vm-env-rules/`

### What it is

The safety and guardrail layer.

### What it does

Defines which operations are allowed, restricted, or confirmation-gated.

### Why it exists

Some operations should be blocked or restricted even if they are technically executable.

### Example use case

`restore_app` may be blocked for production environments regardless of whether the restore stage exists.

---

## 6.9 `tools/`

### What it is

Support utilities.

### What it does

Contains scripts that support the system but are not themselves stages or runtime internals.

### Why it exists

Some support functions need to be available to operators and CI without becoming runtime stage logic.

### Example use case

`tools/ensure_repo.sh` may ensure the repo exists on a remote target before running a stage over SSH.

---

## 6.10 `local-state/`

### What it is

Runtime-created execution state.

### What it does

Stores:

* run metadata
* plan snapshots
* logs
* caches
* locks
* temporary artifacts
* status and resume data

### Why it exists

The runtime needs persistent state for:

* `status`
* `resume`
* `cancel`
* debugging
* CI artifact upload

### Example use case

A failed deploy can still produce a `run_id`, and the operator can inspect logs or retry safely.

---

## 6.11 `.github/workflows/`

### What it is

The thin automation layer.

### What it does

Provides:

* validation workflows
* one reusable execution workflow
* thin wrappers for specific operations

### Why it exists

CI should automate the runtime, not replace it.

### Example use case

A wrapper workflow such as `backup-n8n-prod.yml` can call the reusable workflow with safe defaults and approvals.

---

# 7. End-State Operating Modes

The system supports three valid and intentional modes.

---

## 7.1 Mode A: Manual Skill Mode (inside VM)

### What it is

A skill or operator invokes `vmcx` locally from inside the VM itself.

### Why it exists

This is how bootstrap and experimentation are done before a VM is reliably SSH-managed.

### Best for

* initial VM prep
* local install
* Cloudflare setup
* troubleshooting
* cleanup
* experimentation

### Example

Inside a fresh VM clone:

```bash
./runtime/vmcx plan --target n8n-stage-1 --stages vm_install,cloudflare_vm_access --exec-mode local
./runtime/vmcx run --target n8n-stage-1 --stages vm_install,cloudflare_vm_access --confirm --exec-mode local
```

### Practical guide example

A newly provisioned Ubuntu VM has no trusted SSH key setup yet. You clone the repo manually and run:

```bash
./runtime/vmcx doctor
./runtime/vmcx run --target bootstrap-local --stages vm_install --confirm --exec-mode local
```

That prepares the VM locally before any remote workflow is attempted.

---

## 7.2 Mode B: Operator CLI Mode (control machine)

### What it is

An operator runs `vmcx` from a control machine and uses local or SSH execution.

### Why it exists

This allows structured and repeatable remote operations once targets are ready.

### Best for

* controlled remote deploys
* fan-out operations
* group maintenance
* operator-driven backups

### Example

```bash
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Group example

```bash
vmcx run-group --group prod-app-vms --stages app_deploy --concurrency 2 --confirm --exec-mode ssh
```

### Practical guide example

After two VMs are fully prepared and marked SSH-ready, an operator wants to roll out an app-only change to both VMs:

```bash
vmcx run-group --group n8n-prod-cluster --stages repo_clone_or_update,app_deploy --concurrency 1 --confirm --exec-mode ssh
```

---

## 7.3 Mode C: GitHub Actions Mode (CI/CD)

### What it is

A GitHub Actions workflow calls the same runtime and stage system over SSH.

### Why it exists

To automate validated operations without creating a second orchestration layer.

### Best for

* repeatable deploys
* repeatable backups
* restore with approval
* safe operational automation

### Example execution chain

```text
GitHub Action
  → reusable workflow
  → vmcx
  → SSH executor
  → stage scripts
```

### Practical guide example

A production deploy is approved and triggered through GitHub Actions. The workflow performs:

1. validation
2. secret resolution
3. SSH setup
4. `vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh`
5. log upload

---

# 8. Core Runtime Interface

The runtime is exposed through the `vmcx` CLI.

---

## 8.1 CLI Commands

### Plan by target

```bash
vmcx plan --target <id> --stages <csv> [--params <json>] [--exec-mode auto|local|ssh]
```

### Plan by alias

```bash
vmcx plan --alias <name> [--params <json>] [--exec-mode auto|local|ssh]
```

### Run by target

```bash
vmcx run --target <id> --stages <csv> [--params <json>] --confirm [--exec-mode auto|local|ssh]
```

### Run by alias

```bash
vmcx run --alias <name> [--params <json>] --confirm [--exec-mode auto|local|ssh]
```

### Group run

```bash
vmcx run-group --group <name> --stages <csv> --concurrency <n> --confirm [--exec-mode auto|local|ssh]
```

### Run status

```bash
vmcx status --run-id <id>
```

### Resume

```bash
vmcx resume --run-id <id>
```

### Cancel

```bash
vmcx cancel --run-id <id>
```

### Discovery

```bash
vmcx list-targets
vmcx list-groups
vmcx list-aliases
```

### Diagnostics

```bash
vmcx doctor
```

---

## 8.2 Why these commands exist

These commands support the full lifecycle:

* discovery
* planning
* controlled execution
* multi-target execution
* diagnostics
* operational continuity

They reflect what operators actually need.

---

## 8.3 CLI examples

### Example: inspect available targets

```bash
vmcx list-targets
```

### Example: preview an app deploy

```bash
vmcx plan --alias n8n-app-deploy --exec-mode ssh
```

### Example: execute app deploy

```bash
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Example: check run status

```bash
vmcx status --run-id run-2026-03-06-001
```

### Example: backup one app VM directly

```bash
vmcx run --target n8n-prod-1 --stages backup_app --confirm --exec-mode ssh
```

### Example: restore in staging with params

```bash
vmcx run --alias n8n-app-restore-staging \
  --params '{"backup_id":"bkp-2026-03-06-001","force":false}' \
  --confirm \
  --exec-mode ssh
```

---

# 9. Inventory Contracts

The inventory folder defines what infrastructure exists and how friendly operations map onto it.

---

## 9.1 `vm-configs/vm-groups/vm-machines.yaml`

### What it defines

Real target machines or hosts.

### Contract

* `target_id`
* `target_type` (`vm|host`)
* `environment` (`dev|stage|prod`)
* `labels[]`
* `enabled_stages[]`
* `shared_vm_config`
* `role_specifc_vm_config`
* `target_specifc_vm_config`
* `exec_mode` (`local|ssh`)
* `repo_path`
* `ssh`

  * `host`
  * `user`
  * `port`
  * `key_ref`
* `vars{}`

### Example

```yaml
targets:
  n8n-stage-1:
    target_type: vm
    environment: stage
    labels: [n8n, app, cloudflare]
    enabled_stages:
      - repo_clone_or_update
      - vm_install
      - cloudflare_vm_access
      - cloudflare_app_access
      - app_deploy
      - cleanup_vm
      - backup_app
      - restore_app
    shared_vm_config: default
    role_specifc_vm_config: n8n-app-vm
    target_specifc_vm_config: n8n-stage-1
    exec_mode: ssh
    repo_path: /opt/vm-codex-v2
    ssh:
      host: 10.10.0.20
      user: ubuntu
      port: 22
      key_ref: infisical://vm-codex/ssh/n8n-stage-1
    vars:
      app_id: n8n
```

### Why it matters

This is the machine registry that the runtime uses to understand the environment.

---

## 9.2 `vm-configs/vm-groups/vm-group.yaml`

### What it defines

Logical collections of targets.

### Example

```yaml
groups:
  n8n-stage:
    members:
      - n8n-stage-1

  prod-app-vms:
    members:
      - n8n-prod-1
      - coolify-prod-1
```

### Why it matters

Group runs enable controlled orchestration across multiple targets.

### Example use case

Run backups for all prod app VMs:

```bash
vmcx run-group --group prod-app-vms --stages backup_app --concurrency 1 --confirm --exec-mode ssh
```

---

## 9.3 `vm-configs/vm-groups/vm-set-of-setups.yaml`

### What it defines

Human-friendly named operations.

### Example

```yaml
aliases:
  n8n-vm-install:
    target_selector: target_id=n8n-stage-1
    default_stages:
      - repo_clone_or_update
      - vm_install
      - cloudflare_vm_access
    default_params: {}
    requires_confirmation: true
    description: Prepare the n8n staging VM for operations

  n8n-app-deploy:
    target_selector: target_id=n8n-prod-1
    default_stages:
      - repo_clone_or_update
      - app_deploy
    default_params:
      app_id: n8n
    requires_confirmation: true
    description: Deploy n8n app layer to production
```

### Why it matters

Aliases let humans operate the system using task language instead of raw plumbing.

### Example use case

A skill hears “deploy n8n prod” and maps it directly to alias `n8n-app-deploy`.

---

# 10. Profiles and Configuration Resolution

Profiles define how a machine should behave.

---

## 10.1 Profile layout

```text
vm-configs/vm-profiles/
├─ shared_vm_config/
│  └─ default.yaml
└─ specifc_vm_config/
   └─ *.yaml
```

---

## 10.2 Profile purpose

### Base profile

Global defaults.

### Role overlay

Reusable role-specific config.

### Target overlay

Host-specific overrides.

---

## 10.3 Merge precedence

The system merges config in this order:

1. shared_vm_config profile
2. role overlay
3. target overlay
4. alias defaults
5. explicit CLI or workflow params

### Why this order

It moves from general to specific.

---

## 10.4 Example

### Base profile

```yaml
logging:
  level: info

repo:
  branch: main

runtime:
  shell: bash
```

### Role overlay

```yaml
docker:
  install: true

packages:
  - curl
  - git
  - docker.io
```

### Target overlay

```yaml
repo:
  path: /opt/vm-codex-v2

vars:
  public_hostname: n8n-stage.example.com
```

### Alias defaults

```yaml
default_params:
  app_id: n8n
```

### CLI override

```bash
vmcx run --alias n8n-app-deploy --params '{"image_tag":"2026.03.06"}' --confirm --exec-mode ssh
```

Final merged output now includes all of the above, with the image tag override at highest precedence.

---

# 11. Stage System

All real operational logic lives in `vm-setups/`.

---

## 11.1 Required initial stages

1. `repo_clone_or_update`
2. `vm_install`
3. `cloudflare_vm_access`
4. `cloudflare_app_access`
5. `app_deploy`
6. `cleanup_vm`
7. `backup_app`
8. `restore_app`

---

## 11.2 Stage design rules

Every stage must be:

* idempotent where possible
* callable locally
* callable over SSH
* policy-aware
* testable
* documented
* structured enough to grow safely

---

## 11.3 Stage folder contract

Recommended structure:

```text
vm-setups/<stage_id>/
├─ stage.sh
├─ stage.yaml
├─ scripts/
├─ templates/
├─ tests/
└─ README.md
```

Some stages may also include:

* `adapters/`
* `manifests/`
* `fixtures/`

---

## 11.4 `stage.yaml` example

```yaml
stage_id: app_deploy
description: Deploy or update application workloads on the target
entrypoint: stage.sh

supports_exec_modes:
  - local
  - ssh

idempotent: true
requires_confirmation: true

allowed_target_types:
  - vm
  - host

required_params:
  - app_id

optional_params:
  - image_tag
  - compose_file
  - health_timeout

policy_tags:
  - deploy
  - mutating
```

### Why this matters

The runtime can inspect and validate stages consistently.

---

# 12. Stage-by-Stage Purpose, Use Cases, and Examples

---

## 12.1 `repo_clone_or_update`

### What it does

Ensures the repo exists and is current on the target.

### Why it exists

All modes need a consistent repo on the target path.

### Use cases

* first-time local clone follow-up
* SSH-run deploy preparation
* CI-run remote execution preparation

### Example

```bash
vmcx run --target n8n-stage-1 --stages repo_clone_or_update --confirm --exec-mode ssh
```

### Practical guide example

A target is SSH-ready but its repo is stale. A deploy wrapper first runs `repo_clone_or_update` before `app_deploy`.

---

## 12.2 `vm_install`

### What it does

Performs shared_vm_config machine preparation.

### Typical responsibilities

* install required packages
* install or validate Docker
* install git
* create directories
* prepare service dependencies
* enforce baseline tooling

### Why it exists

VMs need a known-good baseline before app-layer actions are safe.

### Use cases

* first machine prep
* role transition
* baseline repair
* idempotent reinstall of missing dependencies

### Example

```bash
vmcx run --alias n8n-vm-install --confirm --exec-mode local
```

### Practical guide example

A fresh staging VM is created with only Ubuntu installed. The operator clones the repo and runs:

```bash
./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local
```

This installs Docker, git, curl, creates required paths, and checks runtime prerequisites.

---

## 12.3 `cloudflare_vm_access`

### What it does

Configures VM-level access through Cloudflare-related tooling or access rules.

### Why it exists

VM access setup is part of the real bootstrap flow and should be standardized.

### Use cases

* initial hardening
* secure access enablement
* post-bootstrap access normalization

### Example

```bash
vmcx run --target n8n-stage-1 --stages cloudflare_vm_access --confirm --exec-mode local
```

### Practical guide example

After shared_vm_config install, the VM still needs secure access configuration before it is considered ready for remote automation.

---

## 12.4 `cloudflare_app_access`

### What it does

Configures app-level Cloudflare access.

### Why it exists

Application exposure and VM access are not the same concern.

### Use cases

* publishing app access safely
* managing tunnel/access rules
* aligning app exposure with environment

### Example

```bash
vmcx run --target n8n-stage-1 --stages cloudflare_app_access --confirm --exec-mode ssh
```

### Practical guide example

An app has already been deployed, but it should not be publicly reachable until app access controls are configured.

---

## 12.5 `app_deploy`

### What it does

Deploys or updates the application layer.

### Typical responsibilities

* update repo or app artifacts
* build or pull images
* render compose or config templates
* restart services
* perform health checks

### Why it exists

App deployment is one of the most common repeated operations and must be standardized.

### Use cases

* routine deploy
* patch deployment
* image tag rollout
* config-only redeploy

### Example

```bash
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Example with params

```bash
vmcx run --alias n8n-app-deploy \
  --params '{"image_tag":"2026.03.06","health_timeout":120}' \
  --confirm \
  --exec-mode ssh
```

### Practical guide example

A new n8n release is ready. The deploy alias already knows the correct target and app ID. The operator only overrides the image tag.

---

## 12.6 `cleanup_vm`

### What it does

Performs reversible cleanup and reset actions.

### Typical responsibilities

* remove temp files
* stop and remove experimental containers
* clear cache
* clean logs according to policy
* reset staging state safely

### Why it exists

Experimentation and recovery require a repeatable cleanup path.

### Use cases

* reset staging environment
* clean up a failed experiment
* prepare machine for a fresh retry

### Example

```bash
vmcx run --target n8n-stage-1 --stages cleanup_vm --confirm --exec-mode local
```

### Practical guide example

A staging VM has several leftover test containers and cache directories after failed experiments. Cleanup provides a standard reset path.

---

## 12.7 `backup_app`

### What it does

Creates backup artifacts for the application.

### Typical responsibilities

* database dump
* volume snapshot or archive
* config export
* manifest creation
* checksum output

### Why it exists

Backups should be standardized, repeatable, and auditable.

### Use cases

* scheduled backup
* pre-upgrade backup
* pre-restore snapshot
* operational handoff backup

### Example

```bash
vmcx run --alias n8n-app-backup --confirm --exec-mode ssh
```

### Practical guide example

Before a production deploy, a pre-deploy backup is taken so recovery remains possible.

---

## 12.8 `restore_app`

### What it does

Restores application state from a backup.

### Why it exists

Restore is operationally necessary but risky, so it must be standardized and policy-guarded.

### Use cases

* restore staging from backup
* validate backup integrity
* rehearse recovery in non-prod

### Example

```bash
vmcx run --alias n8n-app-restore-staging \
  --params '{"backup_id":"bkp-2026-03-06-001"}' \
  --confirm \
  --exec-mode ssh
```

### Practical guide example

An operator restores staging from a production-like backup to test a migration safely.

---

# 13. Manual-Bootstrap-First Flow

This is a critical architectural rule.

---

## 13.1 Why manual bootstrap is mandatory

Many VMs are not remotely operable in a safe, consistent way at first.

That means:

* manual bootstrap is not a workaround
* manual bootstrap is the intended first step

---

## 13.2 Required onboarding flow

1. provision VM
2. clone repo manually on VM
3. run local install stage
4. run local Cloudflare setup as needed
5. run local cleanup if needed
6. run `vmcx doctor`
7. enable SSH readiness

   * user
   * key auth
   * sudo policy
   * firewall
   * sshd settings
8. verify SSH access
9. mark target `exec_mode=ssh`
10. allow CLI and CI-based remote execution

---

## 13.3 Full example: first-time VM onboarding

### Situation

A new staging VM is created for n8n.

### Step 1: clone repo manually

```bash
git clone <repo-url> /opt/vm-codex-v2
cd /opt/vm-codex-v2
```

### Step 2: inspect target definitions

```bash
./runtime/vmcx list-targets
```

### Step 3: run doctor

```bash
./runtime/vmcx doctor
```

### Step 4: run shared_vm_config install locally

```bash
./runtime/vmcx run --target n8n-stage-1 --stages vm_install --confirm --exec-mode local
```

### Step 5: configure access locally

```bash
./runtime/vmcx run --target n8n-stage-1 --stages cloudflare_vm_access,cloudflare_app_access --confirm --exec-mode local
```

### Step 6: prepare SSH

Set user, authorized keys, sshd config, firewall rules.

### Step 7: update target inventory to `exec_mode: ssh`

### Step 8: test remote execution from control machine

```bash
vmcx plan --target n8n-stage-1 --stages repo_clone_or_update,app_deploy --exec-mode ssh
```

At this point the target has graduated from manual-only to remotely operable.

---

# 14. Skills UX Contract

Every skill must follow a strict UX contract.

---

## 14.1 Resolve intent

The skill must resolve user intent into:

* alias
* target or group
* stages
* params
* execution mode

---

## 14.2 Print plan summary

The skill must show:

* resolved targets
* stages
* config sources merged
* exact command to be run
* risk notes
* execution mode

---

## 14.3 Require explicit confirmation

Any mutating run must require explicit user confirmation.

---

## 14.4 Return run metadata

After execution, return:

* `run_id`
* status
* next commands:

  * `vmcx status --run-id <id>`
  * `vmcx resume --run-id <id>`
  * `vmcx cancel --run-id <id>`

---

## 14.5 Skill examples

### Example 1

User says:

> “do n8n vm thingy”

Skill response should effectively mean:

* likely alias: `n8n-vm-install`
* likely stages: `repo_clone_or_update,vm_install,cloudflare_vm_access`
* target: `n8n-stage-1`
* execution mode: `local` if bootstrap, `ssh` if ready

Then the skill prints a plan.

### Example 2

User says:

> “deploy only app layer on manual app VM”

The skill resolves to:

* target: the requested VM
* stages: `app_deploy`
* no `vm_install`
* likely `exec_mode=local` if operator is inside VM

### Example 3

User says:

> “backup prod n8n”

The skill resolves to:

* alias: `n8n-app-backup`
* stage: `backup_app`
* execution mode: `ssh`
* environment risk note: production backup

---

# 15. CI Role and Workflow Model

The CI role is now explicitly:

**validation plus SSH and then installation and deployment, then backup and restore**

---

## 15.1 Phase 1: Validation

### What it does

Checks:

* repo structure
* config integrity
* stage discovery
* policy validity
* alias resolution
* runtime readiness

### Why it exists

The repo must be validated before infrastructure mutation begins.

### Workflow

`vm-repo-validate.yml`

### Example

A pull request updates target definitions and a backup wrapper. Validation confirms:

* the target exists
* alias references are valid
* referenced stages exist
* policy still allows the wrapper operation

---

## 15.2 Phase 2: SSH Preparation

### What it does

* resolve Infisical secrets
* create ephemeral SSH credentials
* verify connectivity
* optionally ensure repo state

### Why it exists

Remote operations should fail before mutation if SSH readiness is broken.

### Workflow

`_vm-codex-v2-execute.yml`

### Example

A deploy wrapper is triggered, but SSH connectivity fails. The workflow exits before any stage runs.

---

## 15.3 Phase 3: Installation and Deployment

### What it does

Runs install or deploy stages through the runtime.

### Why it exists

These are the main repeatable post-bootstrap actions.

### Wrapper examples

* `install-n8n-vm.yml`
* `deploy-n8n-prod.yml`

### Example

A staging VM is SSH-ready but needs role-standardized install updates. CI runs install remotely using the same stage as local bootstrap.

---

## 15.4 Phase 4: Backup and Restore

### What it does

Runs backup and restore through the same runtime.

### Why it exists

Backup and restore are operational necessities, but restore is higher risk and must be guarded more tightly.

### Wrapper examples

* `backup-n8n-prod.yml`
* `restore-n8n-staging.yml`

### Example

A restore wrapper requires manual approval and explicit params before staging restore can proceed.

---

# 16. GitHub Actions Architecture

---

## 16.1 Reusable core workflow

File:

```text
.github/workflows/_vm-codex-v2-execute.yml
```

### Inputs

* `operation` (`plan|run`)
* `alias`
* `target`
* `stages`
* `params_json`
* `exec_mode`
* `environment`

### Core behavior

1. checkout repo
2. resolve Infisical secrets
3. prepare SSH credentials if needed
4. verify SSH connectivity
5. ensure repo state if required
6. execute `vmcx plan` or `vmcx run --confirm`
7. upload `local-state/` artifacts

### Why it exists

To centralize execution logic once and keep wrappers thin.

---

## 16.2 Thin wrapper workflows

Examples:

* `install-n8n-vm.yml`
* `deploy-n8n-prod.yml`
* `backup-n8n-prod.yml`
* `restore-n8n-staging.yml`

### What they do

They define:

* safe defaults
* intended target/alias
* approvals
* environment binding
* trigger style

### Why they exist

To give discoverable, purpose-specific workflows without duplicating orchestration logic.

---

## 16.3 Wrapper example: deploy

### Wrapper purpose

Production deploy of n8n.

### Wrapper passes

* alias: `n8n-app-deploy`
* operation: `run`
* exec mode: `ssh`
* environment: `prod`

### Runtime then handles

* target resolution
* policy checks
* stage execution
* run tracking

---

# 17. Security and Secrets Model

---

## 17.1 Source of truth

Infisical is the source of truth.

---

## 17.2 Config rule

Profiles and target configs contain references only.

---

## 17.3 Runtime rule

Secrets are resolved only when needed and redacted from logs.

---

## 17.4 CI rule

Credentials are materialized ephemerally and not persisted in run records.

---

## 17.5 Why this model is correct

It reduces secret sprawl while preserving local-first execution.

---

## 17.6 Example

A target defines:

```yaml
key_ref: infisical://vm-codex/ssh/n8n-prod-1
```

The runtime resolves the key at execution time. The key value is not stored in inventory or logs.

---

# 18. Policy Model

Policies define what operations are allowed and under what conditions.

---

## 18.1 Policy file

```text
vm-configs/vm-env-rules/local-policy.yaml
```

---

## 18.2 Policy coverage

Recommended initial policy coverage:

* allowed stages by environment
* allowed stages by target/group
* restore staging-only restriction
* confirmation requirements
* destructive action gating
* optional label-based protections

---

## 18.3 Example policy

```yaml
rules:
  restore_app:
    allowed_environments:
      - stage
    requires_confirmation: true

  cleanup_vm:
    requires_confirmation: true

  app_deploy:
    allowed_environments:
      - dev
      - stage
      - prod
```

---

## 18.4 Why policy exists

It answers “should this be allowed?” even when the runtime technically can do it.

---

## 18.5 Policy example

An operator tries to run:

```bash
vmcx run --target n8n-prod-1 --stages restore_app --confirm --exec-mode ssh
```

Policy should deny this because restore is staging-only.

---

# 19. Local-State Design

---

## 19.1 What local-state stores

* run plans
* run metadata
* stage logs
* execution status
* caches
* locks
* temporary artifacts

---

## 19.2 Why it exists

The runtime must support:

* run inspection
* resume
* cancel
* debugging
* artifact collection

---

## 19.3 Example structure

```text
local-state/
├─ runs/
│  ├─ run-2026-03-06-001/
│  │  ├─ plan.json
│  │  ├─ merged-config.json
│  │  ├─ stage-log.txt
│  │  ├─ status.json
│  │  └─ redactions.json
├─ cache/
└─ locks/
```

---

## 19.4 Example use case

A deploy partially fails after `repo_clone_or_update` but before health checks pass. The operator can inspect the run and decide whether `resume` is valid.

---

# 20. Requirements Layer

The requirements folder describes readiness expectations.

---

## 20.1 Why it exists

Profiles define configuration shape. Requirements define capability expectations.

---

## 20.2 Example use cases

* global required tools
* role-required services
* target-required paths or binaries

---

## 20.3 Example

A role requirement may specify:

* Docker must be installed
* git must be present
* `/opt/vm-codex-v2` must be writable
* `/var/lib/app-data` must exist

These can be checked in validation and `doctor`.

---

# 21. App Contract

Each app definition should specify app-specific operations.

---

## 21.1 File

```text
apps/<app>/app.yaml
```

---

## 21.2 Contract

* `app_id`
* `default_target_group`
* `deploy_stage_params`
* `backup_stage_params`
* `restore_stage_params`
* `health_checks[]`
* `artifacts_policy`

---

## 21.3 Example

```yaml
app_id: n8n
default_target_group: n8n-prod

deploy_stage_params:
  compose_file: docker-compose.yml
  health_timeout: 120

backup_stage_params:
  backup_paths:
    - /var/lib/n8n
  include_db: true

restore_stage_params:
  allowed_environments:
    - stage

health_checks:
  - type: http
    url: https://n8n.example.com/healthz

artifacts_policy:
  retain_logs: true
  retain_manifests: true
```

---

# 22. Validation Plan

Validation should be available both locally and in CI.

---

## 22.1 What must be validated

* repository structure
* stage folder discovery
* `stage.yaml` correctness
* inventory schema correctness
* alias validity
* group integrity
* profile references
* policy references
* app references
* duplicate IDs
* unsupported stage references

---

## 22.2 Why validation matters

This repo is not just source code. It is an operations definition.

Broken structure must be caught early.

---

## 22.3 Validation examples

### Quick local validation

```bash
python3 tools/quick_validate.py
```

### Full runtime validation

```bash
vmcx doctor --ci
```

---

# 23. Testing Plan

---

## 23.1 Unit tests

### Coverage

* alias selector resolution
* merge precedence
* stage metadata loading
* command rendering
* confirmation behavior
* secret redaction
* policy evaluation
* run state transitions

### Example

A unit test verifies alias `n8n-app-deploy` resolves to the correct target and default stage list.

---

## 23.2 Integration tests

### Coverage

* local bootstrap on a fresh VM clone
* SSH mode after readiness flip
* group run with concurrency
* restore blocked in non-staging
* reusable workflow invoking runtime correctly

### Example

An integration test runs `vm_install` locally on a fresh ephemeral VM and asserts Docker and git are installed.

---

## 23.3 End-to-end tests

### E2E 1: vague human intent

Prompt:

```text
do n8n vm thingy
```

Expected:

* intent resolved
* plan shown
* confirmation required
* run executed
* `run_id` returned

### E2E 2: app-only deploy

Prompt:

```text
deploy only app layer on manual app VM
```

Expected:

* stage list only includes `app_deploy`
* no install stages run
* execution mode resolved appropriately

### E2E 3: CI deploy

Workflow:

```text
deploy-n8n-prod.yml
```

Expected:

* validation passes
* SSH ready
* runtime invoked
* app deploy succeeds
* logs uploaded

### E2E 4: backup

Workflow:

```text
backup-n8n-prod.yml
```

Expected:

* backup artifact created
* manifest/log metadata uploaded

### E2E 5: staging restore

Workflow:

```text
restore-n8n-staging.yml
```

Expected:

* staging-only policy passes
* approval required
* explicit params validated
* restore logs captured

---

# 24. Full Use Cases and Guided Examples

This section is intentionally practical and should be treated as operator guidance.

---

## 24.1 Use Case: Bootstrap a fresh VM manually

### Situation

A new VM exists but is not SSH-ready.

### Goal

Prepare the VM locally.

### Steps

1. clone repo manually
2. run `doctor`
3. run `vm_install`
4. configure Cloudflare access
5. prepare SSH
6. flip target to SSH mode

### Example commands

```bash
git clone <repo-url> /opt/vm-codex-v2
cd /opt/vm-codex-v2
./runtime/vmcx doctor
./runtime/vmcx run --target n8n-stage-1 --stages vm_install,cloudflare_vm_access --confirm --exec-mode local
```

### Why this use case matters

This is the canonical first-run path for new machines.

---

## 24.2 Use Case: Deploy app layer from inside a VM

### Situation

You are already inside the VM and only want to redeploy the app layer.

### Goal

Run app deploy without redoing install.

### Example command

```bash
./runtime/vmcx run --target n8n-stage-1 --stages app_deploy --confirm --exec-mode local
```

### Why this use case matters

Not every change requires SSH or CI. Local-first remains valid.

---

## 24.3 Use Case: Deploy remotely from control machine

### Situation

Target is SSH-ready.

### Goal

Run a normal deploy remotely.

### Example command

```bash
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Why this use case matters

This is the normal operator path once bootstrap is complete.

---

## 24.4 Use Case: Deploy to multiple targets

### Situation

You have a group of app VMs.

### Goal

Deploy to all of them in a controlled way.

### Example command

```bash
vmcx run-group --group prod-app-vms --stages repo_clone_or_update,app_deploy --concurrency 1 --confirm --exec-mode ssh
```

### Why this use case matters

Fan-out is essential, but it should still use the same stage logic.

---

## 24.5 Use Case: Backup before deploy

### Situation

A production deploy is about to happen.

### Goal

Create a backup first.

### Example

```bash
vmcx run --alias n8n-app-backup --confirm --exec-mode ssh
vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Why this use case matters

This is a practical safe-change workflow.

---

## 24.6 Use Case: Restore staging from backup

### Situation

You want to test recovery or validate a migration in staging.

### Goal

Restore staging from a known backup artifact.

### Example

```bash
vmcx run --alias n8n-app-restore-staging \
  --params '{"backup_id":"bkp-2026-03-06-001"}' \
  --confirm \
  --exec-mode ssh
```

### Why this use case matters

Restore should be practiced, but only in safe environments initially.

---

## 24.7 Use Case: GitHub Actions deploy

### Situation

A deploy needs to be automated and auditable.

### Goal

Use a wrapper workflow.

### Wrapper

`deploy-n8n-prod.yml`

### Execution model

The wrapper calls `_vm-codex-v2-execute.yml`, which calls `vmcx`.

### Why this use case matters

This is the automation path without duplicating orchestration logic.

---

## 24.8 Use Case: GitHub Actions backup

### Situation

You want repeatable backups via CI.

### Goal

Use a backup wrapper with standard artifacts.

### Wrapper

`backup-n8n-prod.yml`

### Why this use case matters

Backups are a strong fit for standardized CI automation.

---

## 24.9 Use Case: Skill-driven operator flow

### Situation

An operator uses natural language.

### Goal

Resolve intent safely and execute through the runtime.

### Prompt

```text
backup prod n8n
```

### Skill should produce

* resolved alias: `n8n-app-backup`
* target: `n8n-prod-1`
* stage: `backup_app`
* execution mode: `ssh`
* exact command preview

### Why this use case matters

This is the intended operator experience for common tasks.

---

# 25. Rollout Plan

---

## Phase 1: Foundation

### Deliver

* clean scaffold
* runtime shell
* stage discovery
* inventory parsing
* local execution path
* initial skills
* initial stage folders
* validation tooling

### Why

Everything depends on local-first correctness.

### Gate

Manual end-to-end success on one VM.

---

## Phase 2: SSH runtime

### Deliver

* SSH executor
* doctor SSH checks
* repo ensure path
* first SSH-ready target
* remote parity with local stages

### Why

This proves one stage system can operate in both local and remote modes.

### Gate

Remote deploy succeeds using same stage implementation.

---

## Phase 3: CI validation and execution

### Deliver

* validation workflow
* reusable execution workflow
* install/deploy/backup wrappers
* local-state artifact upload

### Why

This adds automation without architectural drift.

### Gate

CI deploy and backup succeed with approvals.

---

## Phase 4: Restore and expansion

### Deliver

* restore wrapper
* stricter restore policy
* more app definitions
* more wrappers
* improved group ops

### Why

Restore should be introduced only after the rest of the system is stable.

### Gate

Restore remains staging-only and auditable.

---

# 26. Updated Recommended Initial Workflow Set

## Validation

* `vm-repo-validate.yml`

## Reusable execution

* `_vm-codex-v2-execute.yml`

## Install

* `install-n8n-vm.yml`

## Deploy

* `deploy-n8n-prod.yml`

## Backup

* `backup-n8n-prod.yml`

## Restore

* `restore-n8n-staging.yml`

This directly matches the updated CI role:

**validation → SSH preparation → installation/deployment → backup/restore**

---

# 27. Updated Recommended Initial Aliases

Examples:

* `n8n-vm-install`
* `n8n-app-deploy`
* `n8n-app-backup`
* `n8n-app-restore-staging`
* `coolify-vm-install`
* `coolify-app-deploy`

Each alias should define:

* target selector
* default stages
* default params
* confirmation requirement
* description

---

# 28. Final “What Goes Where” Summary

| Area                 | What goes there                           | Why                                |
| -------------------- | ----------------------------------------- | ---------------------------------- |
| `ai-skills/`            | human-facing intent resolution            | better operator UX                 |
| `runtime/`           | orchestration engine                      | one place for execution logic      |
| `vm-setups/`            | operational implementations               | all real work lives here           |
| `apps/`              | per-app definitions                       | keep runtime generic               |
| `vm-configs/vm-groups/`         | targets, groups, aliases                  | map the infrastructure             |
| `vm-configs/vm-profiles/`          | reusable config layers                    | reduce duplication                 |
| `vm-configs/requirements/`      | readiness expectations                    | define capability checks           |
| `vm-configs/vm-env-rules/`          | guardrails                                | prevent dangerous actions          |
| `tools/`             | helper utilities                          | support operators and CI           |
| `local-state/`       | logs, run state, locks                    | track what happened                |
| `.github/workflows/` | validation + reusable automation wrappers | automate without duplicating logic |

---

# 29. Final End-State Statement

The end state of `vm-codex-v2` is a **single coherent operations system** where:

* a machine can be bootstrapped manually from inside the VM
* the same operational logic is packaged as reusable stages
* once SSH-ready, the machine can be operated remotely
* GitHub Actions can automate validated remote operations
* no orchestration logic is duplicated across skills, CLI, and CI
* local policy and runtime state provide safety and traceability
* install, deploy, cleanup, backup, and restore are all standardized
* the repo itself remains the source of operational truth

The most important architectural decision is this:

**keep `runtime/` as the engine, keep all real operational logic in `vm-setups/`, and let skills, operator CLI, and GitHub Actions all invoke the same system.**

That is what makes the design scalable, comprehensible, and operationally safe.

If you want, I can turn this into a **formal RFC-style document next**, with sections like **Goals, Non-Goals, Architecture, Contracts, Use Cases, Operational Guide, Rollout, and Open Questions**.
