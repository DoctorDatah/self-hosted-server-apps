# AI-SKILLS_README.MD

## 0. In Plain English (What and Why)
`ai-skills/` is the human-friendly layer on top of raw commands.

What this means in real life:
- A vague request like "deploy n8n prod" can be mapped to a precise command.
- Skills help users avoid memorizing target IDs and stage CSV lists.

Why this exists:
- Improves operator speed and reduces command mistakes.
- Keeps UX guidance separate from execution logic.

## 0.1 First-Time User Start Here
1. Install skills with `bash tools/install_skills.sh`.
2. Read each `SKILL.md` once for expected behavior.
3. Confirm generated command before running mutating operations.

## 0.2 Common Beginner Mistakes
- Mistake: Treating skill docs as executable stage logic.
  Fix: Real logic remains in `vm-setups/` and `runtime/`.
- Mistake: Using stale alias names in skill prompts.
  Fix: Keep skill examples synced with machine `set_of_operations` aliases.

## 0.3 Edit vs Do Not Edit
- Edit skills for operator UX and intent mapping guidance.
- Do not hardcode host internals into skills.

## 1. What This Folder Is About
The `ai-skills/` folder is the operator UX layer for intent-driven workflows.

Skills make operation requests easier for humans by mapping intent to exact runtime commands.

## 2. What It Holds
Current skill folders and purpose:
- `vm-codex-v2-orchestrator`: broad intent routing
- `vm-codex-v2-install`: install/bootstrap flows
- `vm-codex-v2-cloudflare`: access/tunnel setup flows
- `vm-codex-v2-deploy`: app deploy flows
- `vm-codex-v2-cleanup`: reset/cleanup flows
- `vm-codex-v2-backup-restore`: data protection and recovery flows

Each folder contains `SKILL.md` that defines behavior and expected interaction contract.

## 3. How It Relates to Other Components
- Skills resolve to aliases/targets/stages from machine `set_of_operations` (or optional legacy alias file).
- Skills call `runtime/vmcx`; they do not execute stage logic directly.
- Stage behavior remains in `vm-setups/`.
- CI workflows can mirror the same resolved operations for consistency.

## 4. How Users Can Use It and What For
Use skills when operators prefer plain-language guidance and safer command generation.

### Typical operator flow
1. Ask for operation intent (for example deploy or backup).
2. Skill resolves alias, target, and stages then prints exact command.
3. Operator confirms.
4. Runtime executes and returns run ID.

### Install skills locally
- `bash tools/install_skills.sh`

### When to edit skill docs
- You changed aliases or stage conventions and want operator prompts updated.

### What not to do
- Do not implement deploy/install shell scripts in skills.
- Do not duplicate policy logic in skills.

## 5. Examples
### Example: Skill-driven deploy intent
User intent: "deploy n8n prod"
Resolved command:
```bash
./runtime/vmcx run --alias n8n-app-deploy --confirm --exec-mode ssh
```

### Example: Install skills locally
```bash
bash tools/install_skills.sh
```

## 6. Expansion Factor (How This Scales)
Skills scale operator productivity as the number of apps/VMs grows.

Scale pattern:
- Keep skills intent-focused and map to aliases.
- Add or update skills when common tasks become repetitive.
- Do not embed host-specific hardcoding in skill logic.

If you add more teams/operators:
- Standardize phrasing patterns in skill docs.
- Keep output consistent: plan summary + exact command + confirmation.
- Treat skills as UX contracts on top of runtime.
