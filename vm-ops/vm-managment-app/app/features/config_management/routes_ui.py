#!/usr/bin/env python3
import html
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from ...core.app_meta import APP_DISPLAY_NAME, APP_VERSION
from ...core.realtime_bus import bus
from ..ui_system.service import ui_system_template_dirs
from .services import backups, config_store, git_ops, settings as app_settings, validators

router = APIRouter(tags=["config-management-ui"])
templates = Jinja2Templates(directory=ui_system_template_dirs())


def _paths() -> config_store.ConfigPaths:
    return config_store.get_paths()


def _ctx(request: Request, **extra: Any) -> Dict[str, Any]:
    paths = _paths()
    app_timezone = app_settings.DEFAULT_TIMEZONE
    backup_status: Dict[str, Any] = {}
    try:
        app_timezone = app_settings.get_timezone(paths.repo_root)
    except Exception:
        app_timezone = app_settings.DEFAULT_TIMEZONE

    try:
        backup_status = backups.get_backup_status(paths)
        backup_status["latest_backup_created_at_display"] = app_settings.format_iso_datetime(
            str(backup_status.get("latest_backup_created_at") or ""),
            app_timezone,
        )
        backup_status["last_restore_at_display"] = app_settings.format_iso_datetime(
            str(backup_status.get("last_restore_at") or ""),
            app_timezone,
        )
    except Exception:
        backup_status = {}

    return {
        "request": request,
        "app_display_name": APP_DISPLAY_NAME,
        "app_version": APP_VERSION,
        "app_timezone": app_timezone,
        "nav_mode": "config",
        "backup_status": backup_status,
        "config_feature_paths": {
            "dashboard": "/config-management",
            "machines": "/config-management/machines",
            "operations": "/config-management/operations",
            "env_rules": "/config-management/env-rules",
            "backups": "/config-management/backups",
            "git_commits": "/config-management/git-commits",
            "source_of_truth": "/config-management/source-of-truth",
            "home": "/",
        },
        **extra,
    }


def _bool_from_form(form: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = form.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "yes", "y"}


def _split_csv(raw: str) -> List[str]:
    return config_store.split_csv_values(raw)


def _introduced_errors(before: List[str], after: List[str]) -> List[str]:
    base = set(before)
    return [e for e in after if e not in base]


def _md_inline_render(text: str) -> str:
    value = html.escape(str(text or ""))
    # Inline code first to avoid nested replacements interfering.
    value = re.sub(r"`([^`]+)`", r"<code>\1</code>", value)
    value = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", value)
    value = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", value)
    value = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>',
        value,
    )
    return value


def _basic_markdown_to_html(raw_text: str) -> str:
    lines = str(raw_text or "").splitlines()
    out: List[str] = []
    in_list = False
    in_code = False
    code_lines: List[str] = []
    para_lines: List[str] = []

    def flush_paragraph() -> None:
        nonlocal para_lines
        if not para_lines:
            return
        text = " ".join(x.strip() for x in para_lines if x.strip())
        if text:
            out.append(f"<p>{_md_inline_render(text)}</p>")
        para_lines = []

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            out.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = str(raw_line)
        stripped = line.strip()

        if stripped.startswith("```"):
            flush_paragraph()
            flush_list()
            if in_code:
                code_content = "\n".join(code_lines)
                out.append(f"<pre><code>{html.escape(code_content)}</code></pre>")
                code_lines = []
                in_code = False
            else:
                in_code = True
            continue

        if in_code:
            code_lines.append(line)
            continue

        if not stripped:
            flush_paragraph()
            flush_list()
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            flush_list()
            level = len(heading_match.group(1))
            content = _md_inline_render(heading_match.group(2))
            out.append(f"<h{level}>{content}</h{level}>")
            continue

        if stripped.startswith("- ") or stripped.startswith("* "):
            flush_paragraph()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append(f"<li>{_md_inline_render(stripped[2:])}</li>")
            continue

        para_lines.append(stripped)

    flush_paragraph()
    flush_list()
    if in_code:
        code_content = "\n".join(code_lines)
        out.append(f"<pre><code>{html.escape(code_content)}</code></pre>")

    return "\n".join(out) if out else "<p class='muted'>No notes yet.</p>"


def _render_markdown_safe(raw_text: Any) -> str:
    text = str(raw_text or "").strip()
    if not text:
        return "<p class='muted'>No notes yet.</p>"

    try:
        import markdown  # type: ignore

        safe_text = html.escape(text)
        rendered = markdown.markdown(
            safe_text,
            extensions=["nl2br", "sane_lists"],
        )
        return rendered
    except Exception:
        return _basic_markdown_to_html(text)


def _config_readme(topic: str) -> Dict[str, Any]:
    docs: Dict[str, Dict[str, Any]] = {
        "machines": {
            "title": "Manage Machines README",
            "summary": (
                "This page is the machine register for your whole VM operations system. "
                "If a machine entry is wrong, operations can run on the wrong host or fail at runtime."
            ),
            "back_link": "/config-management/machines",
            "back_label": "Manage Machines",
            "sections": [
                {
                    "heading": "What This Page Is About",
                    "intro": (
                        "Machines are the real servers/VMs your runtime is allowed to touch. "
                        "Think of this page as your infrastructure phonebook."
                    ),
                    "points": [
                        "Each row represents one real machine, identified by `machine_id`.",
                        "Operations point to these machine IDs, so IDs must stay stable and unique.",
                        "Rules are enforced using machine environment values (`dev`, `stage`, `prod`).",
                        "If this list is incomplete, your runtime cannot plan or run safely.",
                    ],
                },
                {
                    "heading": "Why This Matters In Simple Terms",
                    "intro": "If machines are wrong here, everything above this layer becomes unreliable.",
                    "points": [
                        "Wrong machine entry means deploy can target wrong host.",
                        "Wrong environment means policy checks can allow or block incorrectly.",
                        "Wrong exec mode or SSH values means runtime fails when it tries to connect.",
                        "Wrong enabled setups can let users run actions that machine should never run.",
                    ],
                },
                {
                    "heading": "What This Page Holds (Field-By-Field)",
                    "points": [
                        "`machine_id`: Permanent key used by operations and group membership.",
                        "`status`: lifecycle state (`active`, `inactive`, `not-setup-yet`).",
                        "`target_type`: Use your model values like `app-vm` or `host-vm` so intent is clear.",
                        "`env`: Policy scope for safety (dev/stage/prod).",
                        "`exec_mode`: `vm-local` for inside-machine runs, `vm-remote-ssh` for remote runs, `vm-both` for both paths.",
                        "`repo_path`: Where `vm-ops` is expected on that machine.",
                        "`notes`: Markdown notes for operator context, runbook hints, and cautions.",
                        "`labels`: Search and organization tags.",
                        "`groups`: Logical collections used for fan-out and reporting.",
                        "`enabled_setups`: Explicit allow-list of setups this machine can run.",
                        "`current_setup_checklist`: Personal checked list of setups already executed on this machine.",
                        "`set_of_operations`: Named setup chains per machine (example: `deploy-the-app-set`).",
                        "`ssh.host`, `ssh.user`, `ssh.port`, `ssh.key_ref`: Required for SSH mode.",
                        "Click `machine_id` in table to open dedicated Machine Access details (vm_link, main_user, SSH fields, jump host notes).",
                        "`params` and `defaults`: Machine-specific values merged into execution context.",
                    ],
                },
                {
                    "heading": "When To Edit vs When Not To Edit",
                    "points": [
                        "Edit when you add/remove a VM.",
                        "Edit when machine environment changes (stage to prod, prod to stage).",
                        "Edit when SSH details rotate or bootstrap mode changes vm-local -> vm-remote-ssh/vm-both.",
                        "Do not change `machine_id` casually; it can break linked operations.",
                        "Do not add setups to `enabled_setups` unless that machine is truly prepared for them.",
                    ],
                },
                {
                    "heading": "What Updating Machines Achieves",
                    "points": [
                        "Runtime `plan` resolves to real infrastructure correctly.",
                        "Runtime `run` can execute safely with proper connectivity details.",
                        "Group operations include the right machines and skip wrong ones.",
                        "Operations and rules stay referentially correct and predictable.",
                    ],
                },
                {
                    "heading": "Safe Editing Workflow (Recommended)",
                    "points": [
                        "Create a config backup first.",
                        "If possible, work on a dedicated config branch from the UI branch tools.",
                        "Add or edit machine entry with complete fields.",
                        "Save and resolve any validation or integrity errors immediately.",
                        "Review operations that depend on this machine ID.",
                        "Run `vmcx plan` for at least one related operation before production runs.",
                    ],
                    "example": (
                        "Example: adding a second production VM\n"
                        "1) Create backup with label `before-adding-prod-2`.\n"
                        "2) Add `n8n-prod-2` as `target_type=app-vm`, `env=prod`, `exec_mode=vm-remote-ssh`.\n"
                        "3) Set `enabled_setups` to only approved setups (for example deploy and backup).\n"
                        "4) Fill SSH host/user/key reference.\n"
                        "5) Save, then update related operation(s) if needed.\n"
                        "6) Run `vmcx plan --alias <deploy-alias> --exec-mode ssh` to verify."
                    ),
                },
                {
                    "heading": "Referential Integrity You Should Know",
                    "points": [
                        "Operations reference `machine_id` directly. Deleting a machine impacts operations.",
                        "Groups must only contain existing machine IDs.",
                        "Enabled setup IDs must exist in `vm-setups`.",
                        "Delete flow can cascade. Always read impact preview before confirming.",
                        "If integrity fails, save should be blocked until references are repaired.",
                    ],
                },
                {
                    "heading": "Scaling Guidance (More VMs, More Environments)",
                    "points": [
                        "Use stable naming conventions: `<app>-<env>-<index>` (example: `n8n-prod-2`).",
                        "Use labels for ownership, app, and lifecycle (example: `app`, `n8n`, `prod`).",
                        "Keep environment boundaries strict; avoid mixing stage/prod semantics.",
                        "Prefer adding machines and operations incrementally, then validate after each batch.",
                        "For large fleets, rely on groups for fan-out instead of copying operations repeatedly.",
                    ],
                },
                {
                    "heading": "Common Mistakes and Quick Fixes",
                    "points": [
                        "Mistake: `machine_id` typo. Fix: correct ID and re-link operations.",
                        "Mistake: missing SSH values in `exec_mode=vm-remote-ssh`. Fix: provide host/user/key_ref and test connectivity.",
                        "Mistake: wrong environment tag. Fix: set correct env and re-run plan for guarded setups.",
                        "Mistake: too many enabled setups. Fix: reduce to minimum required set per machine.",
                        "Mistake: accidental deletion. Fix: restore from Config Backups and validate again.",
                    ],
                },
                {
                    "heading": "Use Cases",
                    "points": [
                        "Onboard new VM after manual bootstrap.",
                        "Promote staging VM config to production-ready values.",
                        "Rotate SSH key references or host values after hardening.",
                        "Restrict machine capabilities by reducing enabled setups.",
                    ],
                },
                {
                    "heading": "Worked Example",
                    "example": (
                        "Use case: move a machine from local-bootstrap to SSH-managed\n"
                        "1) In Manage Machines, locate machine `n8n-stage-1`.\n"
                        "2) Set `exec_mode` from `vm-local` to `vm-remote-ssh`.\n"
                        "3) Fill `ssh.host`, `ssh.user`, `ssh.port`, `ssh.key_ref`.\n"
                        "4) Save and confirm validation has no SSH-related errors.\n"
                        "5) In terminal, test with: vmcx plan --target n8n-stage-1 --stages repo_clone_or_update --exec-mode ssh"
                    ),
                },
                {
                    "heading": "How This Relates To Other Config Tabs",
                    "points": [
                        "Manage Machines defines what exists.",
                        "Manage Operations defines what actions run on what machine.",
                        "Manage Env Rules defines where each setup is allowed.",
                        "Config Backups protects all these files before risky edits.",
                        "Branch and Commit is used to isolate and review config-only changes.",
                    ],
                },
            ],
        },
        "operations": {
            "title": "Manage Operations README",
            "summary": (
                "This page defines reusable run recipes. Each operation maps user intent to one machine and an ordered setup flow."
            ),
            "back_link": "/config-management/operations",
            "back_label": "Manage Operations",
            "sections": [
                {
                    "heading": "What This Page Is About",
                    "intro": (
                        "Operations are named workflows that reduce manual command complexity. "
                        "Think of each operation as a saved runbook entry."
                    ),
                    "points": [
                        "Each operation has one `operation_id` and one target `machine_id`.",
                        "Each operation defines ordered `setups` that execute top to bottom.",
                        "Each operation can include default params and confirmation requirements.",
                        "Operators and automation should rely on operation names instead of ad hoc setup lists.",
                    ],
                },
                {
                    "heading": "Why This Matters In Simple Terms",
                    "points": [
                        "Without operations, users must handcraft every run and will make mistakes.",
                        "Operation naming documents intent clearly (deploy, backup, restore).",
                        "Consistent setup order reduces drift between people and between local and CI runs.",
                    ],
                },
                {
                    "heading": "What This Page Holds",
                    "points": [
                        "`operation_id`: Human-meaningful name for a repeatable action.",
                        "`machine_id`: The machine this operation targets.",
                        "`setups`: Ordered list of setup IDs (execution order matters).",
                        "`params`: Operation-level default params merged at run time.",
                        "`requires_confirmation`: Explicit safety gate for mutating runs.",
                        "`description`: Plain-language explanation of what this operation does.",
                    ],
                },
                {
                    "heading": "When To Edit vs When Not To Edit",
                    "points": [
                        "Edit when you introduce a new repeatable workflow.",
                        "Edit when setup order must change due to dependency changes.",
                        "Edit when machine mapping changes after infrastructure updates.",
                        "Do not create duplicate operations with tiny name differences.",
                        "Do not hide risky actions in generic names like `run-all`.",
                    ],
                },
                {
                    "heading": "What Updating Operations Achieves",
                    "points": [
                        "Reliable, documented run paths for humans and CI.",
                        "Lower cognitive load: operators call one operation ID.",
                        "Auditability: operation changes are visible in git history.",
                        "Predictable execution: setup order is explicit and reviewable.",
                    ],
                },
                {
                    "heading": "How To Think About Setup Order",
                    "points": [
                        "Setups execute in listed order, not alphabetical order.",
                        "Place preparation/setup steps before mutating app steps.",
                        "Keep recovery/destructive operations separate and clearly named.",
                        "If a setup depends on artifact freshness, include `repo_clone_or_update` first.",
                    ],
                    "example": (
                        "Good patterns:\n"
                        "repo_clone_or_update -> app_deploy\n\n"
                        "backup_app -> app_deploy\n\n"
                        "restore_app should usually be its own dedicated operation,\n"
                        "not mixed into a deploy operation."
                    ),
                },
                {
                    "heading": "Referential Integrity You Should Know",
                    "points": [
                        "`operation.machine_id` must match an existing machine entry.",
                        "Every setup in `setups` must exist under `vm-setups`.",
                        "Setup must be enabled on the target machine when enforced.",
                        "Deleting a machine can cascade delete linked operations after confirmation.",
                        "Validation should block save when references are broken.",
                    ],
                },
                {
                    "heading": "Scaling Guidance (Growing From 5 to 100+ Operations)",
                    "points": [
                        "Use consistent naming by intent and scope (example: `n8n-prod-deploy`).",
                        "Keep operations small and composable instead of giant all-in-one chains.",
                        "Separate prod operations from stage/dev operations for clarity and safety.",
                        "Prefer params for small variations; avoid cloning nearly identical operations.",
                        "Review operation list regularly and delete stale ones with cascade preview.",
                    ],
                },
                {
                    "heading": "Common Mistakes and Quick Fixes",
                    "points": [
                        "Mistake: machine reference removed. Fix: reassign operation to valid machine or delete it.",
                        "Mistake: setup typo. Fix: pick valid setup IDs from available list only.",
                        "Mistake: wrong order (deploy before repo update). Fix: reorder setups.",
                        "Mistake: no confirmation on risky flow. Fix: enable `requires_confirmation`.",
                        "Mistake: unclear name. Fix: rename to explicit action + env pattern.",
                    ],
                },
                {
                    "heading": "End-To-End Example",
                    "example": (
                        "Goal: create safe production deploy operation\n"
                        "1) operation_id: n8n-prod-deploy\n"
                        "2) machine_id: n8n-prod-1\n"
                        "3) setups: [repo_clone_or_update, app_deploy]\n"
                        "4) requires_confirmation: true\n"
                        "5) params: {\"app_id\":\"n8n\"}\n"
                        "6) save and validate\n"
                        "7) run: vmcx plan --alias n8n-app-deploy --exec-mode ssh"
                    ),
                },
                {
                    "heading": "Use Cases",
                    "points": [
                        "Create a standard deploy operation for each production app VM.",
                        "Create a backup-first operation before major changes.",
                        "Create a staging restore operation with strict naming and confirmation.",
                        "Create emergency rollback operation patterns with explicit wording.",
                    ],
                },
                {
                    "heading": "Worked Example",
                    "example": (
                        "Use case: app-only deploy from an already prepared machine\n"
                        "1) operation_id: n8n-stage-app-only-deploy\n"
                        "2) machine_id: n8n-stage-1\n"
                        "3) setups: [app_deploy]\n"
                        "4) requires_confirmation: true\n"
                        "5) params: {\"app_id\":\"n8n\",\"health_timeout\":120}\n"
                        "6) Save and run plan before execution."
                    ),
                },
            ],
        },
        "env-rules": {
            "title": "Manage Env Rules README",
            "summary": (
                "This page is your safety policy layer. Rules decide where each setup is allowed and whether confirmation is mandatory."
            ),
            "back_link": "/config-management/env-rules",
            "back_label": "Manage Env Rules",
            "sections": [
                {
                    "heading": "What This Page Is About",
                    "intro": "Rules are your operational guardrails. They answer: should this setup be allowed in this environment?",
                    "points": [
                        "Each rule maps to one setup ID (for example `restore_app`).",
                        "Rules declare allowed environments (`dev`, `stage`, `prod`).",
                        "Rules can force confirmation before execution.",
                        "Rules are enforced before setup execution, so they prevent unsafe starts.",
                    ],
                },
                {
                    "heading": "Why This Matters In Simple Terms",
                    "points": [
                        "Without strong rules, human error can become production incidents.",
                        "Rules make safety explicit and versioned, not tribal knowledge.",
                        "Rules keep behavior consistent across local runs, remote runs, and CI runs.",
                    ],
                },
                {
                    "heading": "What This Page Holds",
                    "points": [
                        "`setup_id` reference key (must match existing setup).",
                        "`allowed_environments`: list where setup can run.",
                        "`requires_confirmation`: additional safety confirmation requirement.",
                        "Optional notes/description fields (if present in your schema) for policy intent.",
                    ],
                },
                {
                    "heading": "When To Edit vs When Not To Edit",
                    "points": [
                        "Edit when introducing a new setup ID.",
                        "Edit when environment policy changes (for example stage-only restore).",
                        "Edit when incident review requires tighter safeguards.",
                        "Do not loosen prod rules casually for convenience.",
                        "Do not leave high-risk setups without explicit policy.",
                    ],
                },
                {
                    "heading": "What Updating Rules Achieves",
                    "points": [
                        "Unsafe plans are denied before mutation.",
                        "Confirmation gates are enforced consistently.",
                        "Policy changes are auditable in git history and code review.",
                        "Environment separation stays enforceable as your fleet grows.",
                    ],
                },
                {
                    "heading": "Recommended Baseline Policy Pattern",
                    "points": [
                        "Allow deploy in `dev`, `stage`, `prod`, usually with confirmation.",
                        "Allow restore only in `stage` initially.",
                        "Allow cleanup in non-prod first; expand only after confidence.",
                        "Treat backup as widely allowed but still reviewed.",
                    ],
                    "example": (
                        "Example baseline rules:\n"
                        "app_deploy:\n"
                        "  allowed_environments: [dev, stage, prod]\n"
                        "  requires_confirmation: true\n\n"
                        "restore_app:\n"
                        "  allowed_environments: [stage]\n"
                        "  requires_confirmation: true"
                    ),
                },
                {
                    "heading": "Referential Integrity You Should Know",
                    "points": [
                        "Rule setup ID must exist in `vm-setups`.",
                        "Invalid setup IDs should fail validation and block save.",
                        "If a setup is removed from code, remove or update its rule too.",
                        "Policy and operations must stay in sync to avoid run-time confusion.",
                    ],
                },
                {
                    "heading": "Scaling Guidance (As Policies Grow)",
                    "points": [
                        "Start with strict defaults, then loosen intentionally where needed.",
                        "Use explicit policy reviews for prod-impacting rule changes.",
                        "Keep rules readable and short; avoid hidden policy behavior.",
                        "Document why a risky setup is allowed in a broader environment.",
                        "Periodically audit for stale rules tied to removed setups.",
                    ],
                },
                {
                    "heading": "Common Mistakes and Quick Fixes",
                    "points": [
                        "Mistake: restore allowed in prod unintentionally. Fix: restrict to stage immediately.",
                        "Mistake: no confirmation for mutating setup. Fix: set confirmation true.",
                        "Mistake: missing rule for new setup. Fix: add rule before using setup in operations.",
                        "Mistake: stale setup ID. Fix: map rule to current setup ID and revalidate.",
                        "Mistake: over-broad allow list. Fix: narrow environments and test with `plan`.",
                    ],
                },
                {
                    "heading": "How This Relates To Other Config Tabs",
                    "points": [
                        "Machines provide environment context used by rules.",
                        "Operations choose setups that rules evaluate.",
                        "Rules are final safety gate before execution.",
                        "Backups let you recover quickly from policy mistakes.",
                    ],
                },
                {
                    "heading": "Use Cases",
                    "points": [
                        "Block restore in production while still allowing stage recovery tests.",
                        "Require confirmation for all deploy flows in production.",
                        "Allow cleanup only in non-production until process is proven safe.",
                        "Tighten rules after incidents or audit findings.",
                    ],
                },
                {
                    "heading": "Worked Example",
                    "example": (
                        "Use case: enforce stage-only restore policy\n"
                        "1) Open Manage Env Rules.\n"
                        "2) Select `restore_app` rule.\n"
                        "3) Set allowed environments to `[stage]` only.\n"
                        "4) Ensure `requires_confirmation` is true.\n"
                        "5) Save and verify `vmcx plan` for prod restore is denied."
                    ),
                },
            ],
        },
    }
    if topic == "rules":
        topic = "env-rules"
    return docs.get(topic, {})


def _normalize_status_path(path: str) -> str:
    raw = str(path or "").strip()
    if " -> " in raw:
        raw = raw.split(" -> ", 1)[1].strip()
    return raw.lstrip("./")


def _config_scoped_changes(changed_files: List[str]) -> List[str]:
    return [_normalize_status_path(p) for p in changed_files if _normalize_status_path(p).startswith("vm-configs/")]


def _git_tracked_paths(paths: config_store.ConfigPaths) -> List[str]:
    tracked = ["vm-configs/vm-machines.yaml"]
    if paths.operations_path.exists():
        tracked.append("vm-configs/vm-operations.yaml")
    if paths.rules_path.exists():
        tracked.append("vm-configs/vm-env-rules.yaml")
    backups_dir = paths.repo_root / "vm-configs" / "config-backups"
    if backups_dir.exists():
        tracked.append("vm-configs/config-backups")
    return tracked


def _machine_payload_from_form(form: Dict[str, Any]) -> Dict[str, Any]:
    machine_id = str(form.get("machine_id", "")).strip()
    original_machine_id = str(form.get("original_machine_id", "")).strip()

    params = validators.parse_json_text(str(form.get("params_json", "")), "params_json")
    defaults = validators.parse_json_text(str(form.get("defaults_json", "")), "defaults_json")

    ssh_port_raw = str(form.get("ssh_port", "22")).strip() or "22"
    try:
        ssh_port = int(ssh_port_raw)
    except ValueError as exc:
        raise ValueError("ssh_port must be an integer") from exc

    raw_exec_mode = str(form.get("exec_mode", "local")).strip().lower() or "local"
    if raw_exec_mode in {"local", "vm-local"}:
        exec_mode = "vm-local"
    elif raw_exec_mode in {"ssh", "vm-remote-ssh"}:
        exec_mode = "vm-remote-ssh"
    elif raw_exec_mode in {"both", "vm-both"}:
        exec_mode = "vm-both"
    else:
        raise ValueError("exec_mode must be one of: vm-local, vm-remote-ssh, vm-both")

    raw_status = str(form.get("status", "active")).strip().lower().replace("_", "-").replace(" ", "-")
    if raw_status not in {"active", "inactive", "not-setup-yet"}:
        raise ValueError("status must be one of: active, inactive, not-setup-yet")

    enabled_setups = _split_csv(str(form.get("enabled_setups_csv", "")))
    operation_sets = _normalize_machine_operation_sets(
        validators.parse_json_text(str(form.get("set_of_operations_json", "")), "set_of_operations_json"),
        allowed_setup_ids=enabled_setups,
    )

    payload = {
        "type": str(form.get("target_type", "vm")).strip() or "vm",
        "parrent": str(form.get("parrent", form.get("parent", ""))).strip(),
        "status": raw_status,
        "env": str(form.get("environment", "")).strip(),
        "notes": str(form.get("notes", "")).strip(),
        "labels": _split_csv(str(form.get("labels_csv", ""))),
        "groups": _split_csv(str(form.get("groups_csv", ""))),
        "enabled_setups": enabled_setups,
        "current_setup_checklist": _split_csv(str(form.get("current_setup_checklist_csv", ""))),
        "set_of_operations": operation_sets,
        "exec_mode": exec_mode,
        "repo_path": str(form.get("repo_path", "/opt/vm-ops")).strip() or "/opt/vm-ops",
        "ssh": {
            "host": str(form.get("ssh_host", "")).strip(),
            "user": str(form.get("ssh_user", "")).strip(),
            "port": ssh_port,
            "key_ref": str(form.get("ssh_key_ref", "")).strip(),
        },
        "params": params,
        "defaults": defaults,
    }

    if not machine_id:
        raise ValueError("machine_id is required")

    return {
        "machine_id": machine_id,
        "original_machine_id": original_machine_id or None,
        "payload": payload,
    }


def _machine_access_payload_from_form(form: Dict[str, Any]) -> Dict[str, Any]:
    machine_id = str(form.get("machine_id", "")).strip()
    if not machine_id:
        raise ValueError("machine_id is required")

    ssh_port_raw = str(form.get("ssh_port", "22")).strip() or "22"
    try:
        ssh_port = int(ssh_port_raw)
    except ValueError as exc:
        raise ValueError("ssh_port must be an integer") from exc
    if ssh_port <= 0:
        raise ValueError("ssh_port must be greater than 0")

    payload = {
        "machine_id": machine_id,
        "repo_path": str(form.get("repo_path", "/opt/vm-ops")).strip() or "/opt/vm-ops",
        "ssh": {
            "host": str(form.get("ssh_host", "")).strip(),
            "user": str(form.get("main_user", "")).strip(),
            "port": ssh_port,
            "key_ref": str(form.get("ssh_key_ref", "")).strip(),
        },
        "access": {
            "vm_link": str(form.get("vm_link", "")).strip(),
            "jump_host": str(form.get("jump_host", "")).strip(),
            "jump_user": str(form.get("jump_user", "")).strip(),
            "notes": str(form.get("access_notes", "")).strip(),
        },
    }
    return payload


def _machine_notes_payload_from_form(form: Dict[str, Any]) -> Dict[str, Any]:
    machine_id = str(form.get("machine_id", "")).strip()
    if not machine_id:
        raise ValueError("machine_id is required")

    notes_md = str(form.get("notes_md", "")).strip()
    return {
        "machine_id": machine_id,
        "notes": notes_md,
    }


def _machine_setup_checklist_payload_from_form(form: Dict[str, Any]) -> Dict[str, Any]:
    machine_id = str(form.get("machine_id", "")).strip()
    if not machine_id:
        raise ValueError("machine_id is required")

    checklist = _split_csv(str(form.get("current_setup_checklist_csv", "")))
    return {
        "machine_id": machine_id,
        "current_setup_checklist": checklist,
    }


def _apply_machine_access_payload(machine: Dict[str, Any], payload: Dict[str, Any]) -> None:
    ssh = machine.get("ssh", {})
    if not isinstance(ssh, dict):
        ssh = {}
    ssh_in = payload.get("ssh", {})
    if isinstance(ssh_in, dict):
        ssh["host"] = str(ssh_in.get("host", "")).strip()
        ssh["user"] = str(ssh_in.get("user", "")).strip()
        ssh["port"] = int(ssh_in.get("port", 22))
        ssh["key_ref"] = str(ssh_in.get("key_ref", "")).strip()
    machine["ssh"] = ssh

    repo_path = str(payload.get("repo_path", "")).strip()
    if repo_path:
        machine["repo_path"] = repo_path

    access_in = payload.get("access", {})
    access_obj: Dict[str, Any] = {}
    if isinstance(access_in, dict):
        for key in ["vm_link", "jump_host", "jump_user", "notes"]:
            value = str(access_in.get(key, "")).strip()
            if value:
                access_obj[key] = value

    if access_obj:
        machine["access"] = access_obj
    else:
        machine.pop("access", None)


def _normalize_machine_operation_sets(
    raw: Dict[str, Any],
    *,
    allowed_setup_ids: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    if not raw:
        return {}

    if not isinstance(raw, dict):
        raise ValueError("set_of_operations_json must be a JSON object")

    normalized: Dict[str, Dict[str, Any]] = {}
    allowed_setups = {str(x).strip() for x in (allowed_setup_ids or []) if str(x).strip()}
    for set_name_raw, set_body in raw.items():
        set_name = str(set_name_raw or "").strip()
        if not set_name:
            continue
        if not isinstance(set_body, dict):
            raise ValueError(f"set_of_operations '{set_name}' must be an object")

        setups_raw = set_body.get("setups", [])
        if isinstance(setups_raw, str):
            setups = _split_csv(setups_raw)
        elif isinstance(setups_raw, list):
            setups = [str(x).strip() for x in setups_raw if str(x).strip()]
        else:
            raise ValueError(f"set_of_operations '{set_name}' setups must be a list or CSV string")

        if not setups:
            raise ValueError(f"set_of_operations '{set_name}' must include at least one setup")

        if allowed_setups:
            invalid = [sid for sid in setups if sid not in allowed_setups]
            if invalid:
                raise ValueError(
                    f"set_of_operations '{set_name}' includes setup(s) not in enabled_setups: {', '.join(invalid)}"
                )

        normalized_entry: Dict[str, Any] = {"setups": setups}
        description = str(set_body.get("description", "")).strip()
        if description:
            normalized_entry["description"] = description

        params = set_body.get("params")
        if params is not None:
            if not isinstance(params, dict):
                raise ValueError(f"set_of_operations '{set_name}' params must be an object")
            normalized_entry["params"] = params

        normalized[set_name] = normalized_entry

    return normalized


def _operation_payload_from_form(form: Dict[str, Any]) -> Dict[str, Any]:
    operation_id = str(form.get("operation_id", "")).strip()
    original_operation_id = str(form.get("original_operation_id", "")).strip()
    machine_id = str(form.get("machine_id", "")).strip()

    params = validators.parse_json_text(str(form.get("params_json", "")), "params_json")

    if not operation_id:
        raise ValueError("operation_id is required")
    if not machine_id:
        raise ValueError("machine_id is required")

    payload = {
        "machine": machine_id,
        "setups": _split_csv(str(form.get("setups_csv", ""))),
        "params": params,
        "requires_confirmation": _bool_from_form(form, "requires_confirmation", True),
        "description": str(form.get("description", "")).strip(),
    }

    return {
        "operation_id": operation_id,
        "original_operation_id": original_operation_id or None,
        "payload": payload,
    }


def _rule_payload_from_form(form: Dict[str, Any], allowed_envs: List[str]) -> Dict[str, Any]:
    setup_id = str(form.get("setup_id", "")).strip()
    original_setup_id = str(form.get("original_setup_id", "")).strip()
    if not setup_id:
        raise ValueError("setup_id is required")

    payload: Dict[str, Any] = {
        "requires_confirmation": _bool_from_form(form, "requires_confirmation", False)
    }
    if allowed_envs:
        payload["allowed_environments"] = allowed_envs

    return {
        "setup_id": setup_id,
        "original_setup_id": original_setup_id or None,
        "payload": payload,
    }


def _normalize_allowed_environments(values: List[str]) -> List[str]:
    normalized: List[str] = []
    allowed = {"dev", "stage", "prod", "any"}
    seen = set()

    for raw in values:
        env = str(raw or "").strip().lower()
        if not env:
            continue
        if env not in allowed:
            raise ValueError(f"allowed_environments has invalid value: {env}")
        if env in seen:
            continue
        seen.add(env)
        normalized.append(env)

    if "any" in seen:
        # "any" means no environment restriction in persisted config.
        return []

    return [x for x in normalized if x in {"dev", "stage", "prod"}]


def _load_setup_meta(repo_root: Path, setup_id: str) -> Dict[str, Any]:
    setup_path = repo_root / "vm-setups" / setup_id / "stage.yaml"
    if not setup_path.exists():
        raise ValueError(f"Missing setup metadata: {setup_path}")
    raw = setup_path.read_text(encoding="utf-8").strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid setup metadata JSON in {setup_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"Setup metadata must be a JSON object: {setup_path}")
    return data


def _machine_runtime_exec_modes(exec_mode: Any) -> List[str]:
    value = str(exec_mode or "vm-local").strip().lower()
    if value in {"vm-remote-ssh", "ssh"}:
        return ["ssh"]
    if value in {"vm-both", "both"}:
        return ["local", "ssh"]
    return ["local"]


def _machine_runtime_target_type(machine: Dict[str, Any]) -> str:
    raw = str(machine.get("type", machine.get("target_type", "app-vm"))).strip().lower()
    return "host" if raw in {"host", "host-vm"} else "vm"


def _strip_shell_literal(raw: str) -> str:
    value = str(raw or "").strip()
    if len(value) >= 2 and ((value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'"))):
        return value[1:-1]
    return value


def _extract_stage_param_meta(repo_root: Path, setup_id: str) -> Dict[str, Dict[str, Any]]:
    setup_path = repo_root / "vm-setups" / setup_id / "stage.sh"
    if not setup_path.exists():
        return {}

    text = setup_path.read_text(encoding="utf-8")
    meta: Dict[str, Dict[str, Any]] = {}

    bool_pattern = re.compile(r"vmcx_param_bool\s+([A-Za-z0-9_]+)\s+(.+?)\)")
    get_pattern = re.compile(r"vmcx_param_get\s+([A-Za-z0-9_]+)\s+(.+?)\)")

    for match in bool_pattern.finditer(text):
        param_name = str(match.group(1))
        default_raw = _strip_shell_literal(str(match.group(2)))
        lower = default_raw.strip().lower()
        default_value = True if lower in {"1", "true", "yes", "y", "on"} else False
        meta[param_name] = {"kind": "bool", "default": default_value}

    for match in get_pattern.finditer(text):
        param_name = str(match.group(1))
        if param_name in meta:
            continue
        default_raw = _strip_shell_literal(str(match.group(2)))
        meta[param_name] = {"kind": "string", "default": default_raw}

    return meta


def _setup_dynamic_notes(setup_id: str) -> List[str]:
    if setup_id == "vm_install":
        return [
            "`install_*` flags toggle package/tool installation behavior.",
            "`create_network` + `network_name` control Docker network provisioning.",
            "If no value is provided from machine or operation params, stage defaults are used.",
            "Machine params apply across operations; operation params are operation-specific overrides.",
        ]
    return []


def _setup_param_help(setup_id: str, param_names: List[str]) -> Dict[str, List[str]]:
    known: Dict[str, List[str]] = {
        "install_utils": [
            "What: Toggles install of baseline utility packages (for example curl/wget).",
            "Why: Many later setup steps assume these tools are available.",
            "Impact: `true` can install/update packages; `false` skips that step.",
            "When to use: Keep `true` for new VMs, disable only when image already has curated tooling.",
        ],
        "install_git": [
            "What: Toggles git installation check for this VM.",
            "Why: Repo sync and deploy paths require git.",
            "Impact: `true` installs/verifies git; `false` assumes git already exists.",
            "When to use: Leave `true` for bootstrap and drift repair.",
        ],
        "install_python": [
            "What: Toggles python3/pip installation check.",
            "Why: Some scripts/tools rely on Python runtime.",
            "Impact: `true` can install packages; `false` skips Python provisioning.",
            "When to use: Disable only when base image policy manages Python.",
        ],
        "install_docker": [
            "What: Toggles Docker engine provisioning.",
            "Why: App deploy, backup, and cleanup setups typically depend on Docker.",
            "Impact: `true` may install Docker components; `false` assumes Docker already managed.",
            "When to use: Keep enabled for app-vm bootstrap.",
        ],
        "create_network": [
            "What: Toggles Docker network creation step.",
            "Why: Containers may need a stable shared network name.",
            "Impact: `true` ensures network exists; `false` leaves network untouched.",
            "When to use: Enable when compose/services depend on a named network.",
        ],
        "network_name": [
            "What: Name of Docker network to create/use.",
            "Why: Must match container compose/network references.",
            "Impact: Wrong value can break container connectivity.",
            "When to use: Set to your app standard (for example `appnet`).",
        ],
        "install_infisical": [
            "What: Toggles Infisical CLI install.",
            "Why: Required when this VM resolves secrets directly.",
            "Impact: `true` installs CLI and dependencies; `false` skips it.",
            "When to use: Enable only on machines that resolve secrets at runtime.",
        ],
        "install_codex": [
            "What: Toggles Codex CLI install step.",
            "Why: Needed only if this VM runs Codex tooling locally.",
            "Impact: `true` installs tooling; `false` keeps VM leaner.",
            "When to use: Usually `false` on production runtime VMs.",
        ],
        "compose_file": [
            "What: Compose file path used during deploy.",
            "Why: Deploy step reads services and networks from this file.",
            "Impact: Wrong path causes deploy failure.",
            "When to use: Set when app compose file differs from default.",
        ],
        "action": [
            "What: Execution action/mode for the setup (example: up/down/restart).",
            "Why: Changes behavior branch in setup script.",
            "Impact: Can be mutating depending on action value.",
            "When to use: Only set if setup supports action variants.",
        ],
        "app_id": [
            "What: Logical application identifier (example: n8n).",
            "Why: Setup uses this to choose app-specific paths or behavior.",
            "Impact: Wrong app_id can target wrong app resources.",
            "When to use: Set per machine app ownership.",
        ],
        "branch": [
            "What: Git branch name used for repo update step.",
            "Why: Controls which code/config revision the VM receives.",
            "Impact: Branch mismatch can deploy unexpected code.",
            "When to use: Pin to release branch when needed.",
        ],
        "repo_url": [
            "What: Git repository URL for initial clone/update.",
            "Why: Needed when target machine must self-sync repo.",
            "Impact: Wrong URL breaks clone/update.",
            "When to use: Override when using fork/mirror/private remote.",
        ],
        "repo_path": [
            "What: Absolute path of repo on VM.",
            "Why: Setup commands run from this location.",
            "Impact: Wrong path causes stage execution failures.",
            "When to use: Keep aligned with real VM filesystem.",
        ],
        "backup_root": [
            "What: Root path where backup artifacts are written/read.",
            "Why: Backup/restore jobs use this as storage location.",
            "Impact: Wrong path can lose backup visibility or fail writes.",
            "When to use: Set to mounted disk/location with retention policy.",
        ],
        "backup_id": [
            "What: Specific backup identifier to restore/inspect.",
            "Why: Restore must know exactly which artifact to apply.",
            "Impact: Wrong ID restores wrong snapshot or fails.",
            "When to use: Required for targeted restore operations.",
        ],
        "restore_root": [
            "What: Destination base path for restore output.",
            "Why: Controls where restored data is placed.",
            "Impact: Bad path can overwrite wrong data.",
            "When to use: Set explicitly in staging recovery tests.",
        ],
        "restore_target_type": [
            "What: Safety marker for restore target type.",
            "Why: Prevents restore running in unintended context.",
            "Impact: Mismatch should block restore path.",
            "When to use: Keep aligned with intended environment policy.",
        ],
        "force": [
            "What: Bypass/safety override flag.",
            "Why: Allows progress in exceptional blocked conditions.",
            "Impact: Higher risk; can skip guardrails.",
            "When to use: Emergency only, with explicit operator approval.",
        ],
        "full_clean": [
            "What: Enables aggressive cleanup mode.",
            "Why: Used to reset machine state more deeply.",
            "Impact: Can remove containers/data depending on setup flags.",
            "When to use: Recovery/reset workflows, not routine deploys.",
        ],
        "sources": [
            "What: Source paths list used by backup packaging.",
            "Why: Defines what data is actually captured.",
            "Impact: Missing paths means incomplete backups.",
            "When to use: Tune per app data layout.",
        ],
        "backup_paths": [
            "What: Alias list of paths included in backup.",
            "Why: Same role as `sources` in certain setups.",
            "Impact: Inaccurate list reduces backup completeness.",
            "When to use: Keep in sync with real app data directories.",
        ],
        "section": [
            "What: Partial deploy selector (specific section only).",
            "Why: Supports scoped deploy updates without full rollout.",
            "Impact: May skip expected sections if set incorrectly.",
            "When to use: Controlled partial deploy workflows.",
        ],
        "utils_version_pin": [
            "What: Optional package version pin for utils install.",
            "Why: Reproducible install behavior across VMs.",
            "Impact: Invalid pin can break package install.",
            "When to use: Compliance or deterministic environment requirements.",
        ],
        "git_version_pin": [
            "What: Optional git package version pin.",
            "Why: Keeps git version consistent across environments.",
            "Impact: Invalid pin may fail apt install.",
            "When to use: Use only when version standard is required.",
        ],
        "python_version_pin": [
            "What: Optional python package version pin.",
            "Why: Keeps runtime dependencies predictable.",
            "Impact: Invalid/unavailable version fails install.",
            "When to use: Strict compatibility requirements.",
        ],
        "docker_version_pin": [
            "What: Optional Docker package version pin.",
            "Why: Avoids unexpected Docker version drift.",
            "Impact: Pin mismatch can block install/update.",
            "When to use: Production stability windows.",
        ],
        "infisical_version_pin": [
            "What: Optional Infisical CLI version pin.",
            "Why: Keeps secret tool behavior consistent.",
            "Impact: Wrong pin can break CLI install.",
            "When to use: Only when CLI version must be controlled.",
        ],
        "codex_version_pin": [
            "What: Optional Codex CLI version pin.",
            "Why: Prevents accidental version drift for CLI users.",
            "Impact: Invalid npm version fails install.",
            "When to use: Dev tooling standardization.",
        ],
    }
    result: Dict[str, List[str]] = {}
    for name in param_names:
        lines = list(known.get(name, []))
        lowered = str(name or "").lower()
        if not lines:
            pretty = str(name).replace("_", " ")
            lines.append(f"What: `{name}` controls {pretty} behavior for this setup run.")

            if lowered.endswith("_path"):
                lines.append("Why: Path values decide where files/data are read or written.")
                lines.append("Impact: Wrong path can break execution or target wrong data.")
            elif lowered.endswith("_version_pin"):
                lines.append("Why: Version pins provide deterministic package/tool versions.")
                lines.append("Impact: Invalid pin can fail installation.")
            elif lowered.startswith(("remove_", "delete_", "clean_", "uninstall_")):
                lines.append("Why: Cleanup flags control what gets removed.")
                lines.append("Impact: Can be destructive if enabled without review.")
            elif lowered.startswith(("install_", "create_", "enable_")):
                lines.append("Why: Provision flags control installation/provisioning steps.")
                lines.append("Impact: Enabling may install packages or alter runtime state.")
            else:
                lines.append("Why: This parameter tunes setup behavior for machine-specific needs.")
                lines.append("Impact: Wrong value can cause setup mismatch or failure.")

            lines.append("When to use: Override only when this VM needs behavior different from default.")

        lines.append(f"Scope: Applies only when `{setup_id}` runs on this machine.")
        lines.append("Priority: VM value here overrides stage default during execution.")
        result[name] = lines
    return result


def _param_input_type(param_name: str, meta: Optional[Dict[str, Any]], default_value: Any) -> str:
    if isinstance(meta, dict) and str(meta.get("kind", "")).strip().lower() == "bool":
        return "bool"
    if isinstance(default_value, bool):
        return "bool"
    lowered = str(param_name or "").strip().lower()
    bool_prefixes = ("is_", "has_", "enable_", "disable_", "install_", "remove_", "clean_", "force", "full_", "create_", "include_", "uninstall_")
    if lowered.startswith(bool_prefixes):
        return "bool"
    return "string"


def _parse_bool_text(raw: Any, field_name: str) -> bool:
    value = str(raw or "").strip().lower()
    if value in {"1", "true", "yes", "y", "on"}:
        return True
    if value in {"0", "false", "no", "n", "off"}:
        return False
    raise ValueError(f"{field_name} must be true or false")


def _version_pin_for_base(base_name: str, field_by_name: Dict[str, Dict[str, Any]]) -> Optional[str]:
    candidates = [f"{base_name}_version_pin"]
    if base_name.startswith("install_"):
        suffix = base_name[len("install_") :]
        candidates.append(f"{suffix}_version_pin")
    for candidate in candidates:
        if candidate in field_by_name:
            return candidate
    return None


def _base_for_version_pin(version_pin_name: str, field_by_name: Dict[str, Dict[str, Any]]) -> Optional[str]:
    if not version_pin_name.endswith("_version_pin"):
        return None
    stem = version_pin_name[: -len("_version_pin")]
    candidates = [stem, f"install_{stem}"]
    for candidate in candidates:
        if candidate in field_by_name:
            return candidate
    return None


@router.get("/config-management")
@router.get("/features/config-management")
def dashboard(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    status = git_ops.get_status(paths.repo_root)
    config_changed_files = _config_scoped_changes([str(x) for x in status.get("changed_files", [])])
    config_git_status = {
        "is_clean": len(config_changed_files) == 0,
        "changed_files": config_changed_files,
        "change_count": len(config_changed_files),
    }
    validation_errors = validators.validate_bundle(bundle, paths.repo_root)
    backups_count = len(backups.list_backups(paths))

    machines = bundle.machines_doc.get("machines", {})
    operations = bundle.operations_doc.get("operations", {})
    rules = bundle.rules_doc.get("rules", {})

    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request,
            page_title="Config Management Dashboard",
            machines_count=len(machines),
            operations_count=len(operations),
            rules_count=len(rules),
            backups_count=backups_count,
            git_status=status,
            git_status_config=config_git_status,
            validation_errors=validation_errors,
        ),
    )


@router.get("/config-management/git-commits")
@router.get("/features/config-management/git-commits")
def git_commits_page(request: Request):
    paths = _paths()
    cfg = app_settings.load_settings(paths.repo_root)
    timezone_name = str(cfg.get("timezone", app_settings.DEFAULT_TIMEZONE))
    preferred_branch = str(cfg.get("preferred_config_branch", "") or "")
    status = git_ops.get_status(paths.repo_root)
    current_local_branch = str(status.get("branch", "") or "")
    related_prs: List[Dict[str, Any]] = []
    pr_list_error = ""
    related_branches: List[Dict[str, Any]] = []
    branch_list_error = ""
    try:
        related_prs = git_ops.list_open_prs(
            paths.repo_root,
            preferred_branch=preferred_branch,
            related_only=True,
            limit=100,
        )
    except Exception as exc:  # noqa: BLE001
        pr_list_error = str(exc)
    try:
        related_branches = git_ops.list_related_branches(
            paths.repo_root,
            preferred_branch=preferred_branch,
            limit=100,
        )
    except Exception as exc:  # noqa: BLE001
        branch_list_error = str(exc)

    if git_ops.is_related_config_branch(current_local_branch, preferred_branch=preferred_branch):
        selected_target_branch = current_local_branch
        selected_branch_source = "local_related"
    elif related_prs:
        selected_target_branch = str(related_prs[0].get("head", "") or "").strip()
        selected_branch_source = "open_related_pr"
    else:
        resolved_branch, _resolved_exists = git_ops.resolve_target_branch(
            paths.repo_root,
            explicit_branch=None,
            preferred_branch=preferred_branch or None,
            fallback_tz=timezone_name,
        )
        selected_target_branch = resolved_branch
        selected_branch_source = "resolved_related_or_new"
    return templates.TemplateResponse(
        "git_commits.html",
        _ctx(
            request,
            page_title="Branch and Commit",
            git_status=status,
            default_branch=git_ops.default_branch_name(timezone_name),
            selected_target_branch=selected_target_branch,
            selected_branch_source=selected_branch_source,
            preferred_config_branch=preferred_branch,
            default_message=git_ops.default_commit_message(),
            tracked_files=_git_tracked_paths(paths),
            related_open_prs=related_prs,
            pr_list_error=pr_list_error,
            related_branches=related_branches,
            branch_list_error=branch_list_error,
        ),
    )


@router.get("/settings")
def settings_root() -> RedirectResponse:
    return RedirectResponse(url="/settings/timezone", status_code=307)


@router.get("/settings/timezone")
def settings_timezone_page(request: Request):
    paths = _paths()
    cfg = app_settings.load_settings(paths.repo_root)
    timezone_name = str(cfg.get("timezone", app_settings.DEFAULT_TIMEZONE))
    preferred_branch = str(cfg.get("preferred_config_branch", "") or "")
    return templates.TemplateResponse(
        "settings_timezone.html",
        _ctx(
            request,
            page_title="Settings - Time Zone",
            nav_mode="settings",
            current_timezone=timezone_name,
            preferred_config_branch=preferred_branch,
            timezone_options=app_settings.all_timezones(),
        ),
    )


@router.get("/settings/connections")
def settings_connections_page(request: Request):
    paths = _paths()
    github_connection = git_ops.github_connection_status(paths.repo_root)
    return templates.TemplateResponse(
        "settings_connections.html",
        _ctx(
            request,
            page_title="Settings - Connections",
            nav_mode="settings",
            github_connection=github_connection,
            github_device_login_url="https://github.com/login/device",
        ),
    )


@router.post("/settings/save")
async def save_settings(request: Request):
    paths = _paths()
    form = await request.form()
    timezone_name = str(form.get("timezone", "")).strip()
    preferred_branch = str(form.get("preferred_config_branch", "")).strip()
    try:
        saved = app_settings.save_settings(
            paths.repo_root,
            timezone_name=timezone_name,
            preferred_config_branch=preferred_branch,
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Settings save failed: {exc}</div>", status_code=200)

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Settings saved. Timezone: <code>{saved['timezone']}</code>. "
            f"UI target branch: <code>{saved.get('preferred_config_branch', '') or '-'}</code>."
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/settings/connections/github/connect")
async def settings_connect_github(request: Request):
    paths = _paths()
    try:
        result = git_ops.connect_github_web(paths.repo_root, git_protocol="https", hostname="github.com")
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            (
                "<div class='flash error'>"
                f"GitHub connect failed: {exc}<br/>"
                "If browser did not open, run <code>gh auth login --web --git-protocol https</code> in terminal."
                "</div>"
            ),
            status_code=200,
        )
    device_code = str(result.get("device_code", "") or "").strip()
    auth_url = str(result.get("auth_url", "https://github.com/login/device"))
    details = "<div class='flash success'>"
    details += f"{result.get('message', 'GitHub browser OAuth started.')}<br/>"
    if device_code:
        details += (
            "Device Code (enter this on GitHub): "
            f"<code style='font-size:1.1rem;'>{device_code}</code>. "
            f"<button type='button' class='btn ghost small' onclick=\"navigator.clipboard && navigator.clipboard.writeText('{device_code}')\">Copy Code</button><br/>"
            "Paste this code into the GitHub authentication tab.<br/>"
        )
    else:
        details += (
            "<span class='warn'>Device code is not available yet.</span> "
            "GitHub CLI usually copies it to your clipboard automatically.<br/>"
            "If the GitHub page asks for a code, click Connect To GitHub again.<br/>"
        )
    details += (
        "Open authentication page: "
        f"<a class='card-link' href='{auth_url}' target='_blank' rel='noreferrer'>GitHub Device Login</a>.<br/>"
        "After completing browser auth, refresh this page to see Connected status."
        "</div>"
    )
    return HTMLResponse(details, status_code=200)


@router.post("/settings/connections/github/device-code")
async def settings_device_code_github(request: Request):
    code = str(git_ops.read_device_code_hint() or "").strip()
    if code:
        return HTMLResponse(
            (
                "<div class='flash success'>"
                "Device Code: "
                f"<code style='font-size:1.1rem;'>{code}</code>. "
                f"<button type='button' class='btn ghost small' onclick=\"navigator.clipboard && navigator.clipboard.writeText('{code}')\">Copy Code</button>"
                "</div>"
            ),
            status_code=200,
        )
    return HTMLResponse(
        (
            "<div class='flash warn'>"
            "No device code found in clipboard yet. Click Connect To GitHub again, then retry."
            "</div>"
        ),
        status_code=200,
    )


@router.post("/settings/connections/github/disconnect")
async def settings_disconnect_github(request: Request):
    paths = _paths()
    try:
        result = git_ops.disconnect_github(paths.repo_root, hostname="github.com")
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>GitHub disconnect failed: {exc}</div>", status_code=200)
    return HTMLResponse(
        (
            "<div class='flash success'>"
            "GitHub disconnected. Refreshing status.<br/>"
            f"<pre>{result.get('message', '')}</pre>"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/switch")
async def git_switch_branch(request: Request):
    paths = _paths()
    form = await request.form()
    branch_name = str(form.get("branch_name", "")).strip()
    try:
        result = git_ops.switch_branch(paths.repo_root, branch_name)
        app_settings.save_preferred_config_branch(paths.repo_root, result["branch"])
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Branch switch failed: {exc}</div>", status_code=200)
    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"UI target branch set to <code>{result['branch']}</code>. "
            "Your local checked-out branch was not changed."
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/prepare")
async def git_prepare_commit(request: Request):
    paths = _paths()
    form = await request.form()
    branch_name = str(form.get("branch_name", "")).strip()
    commit_message = str(form.get("commit_message", "")).strip()
    cfg = app_settings.load_settings(paths.repo_root)
    timezone_name = str(cfg.get("timezone", app_settings.DEFAULT_TIMEZONE))
    preferred_branch = str(cfg.get("preferred_config_branch", "") or "")
    try:
        result = git_ops.prepare_commit(
            paths.repo_root,
            tracked_files=_git_tracked_paths(paths),
            branch_name=branch_name or None,
            preferred_branch=preferred_branch or None,
            fallback_tz=timezone_name,
            commit_message=commit_message or None,
        )
        app_settings.save_preferred_config_branch(paths.repo_root, str(result.get("branch", "")))
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Commit failed: {exc}</div>", status_code=200)

    files_html = "".join(f"<li><code>{f}</code></li>" for f in result.get("changed_files", []))
    next_cmds = "".join(f"<li><code>{c}</code></li>" for c in result.get("next_commands", []))
    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Committed on <code>{result['branch']}</code> at <code>{result['commit_sha']}</code>."
            "</div>"
            "<div class='panel'>"
            "<h4>Changed Files</h4>"
            f"<ul class='simple-list'>{files_html or '<li>-</li>'}</ul>"
            "<h4>Next Commands</h4>"
            f"<ul class='simple-list'>{next_cmds or '<li>-</li>'}</ul>"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/commit-only")
async def git_commit_only(request: Request):
    paths = _paths()
    form = await request.form()
    branch_name = str(form.get("branch_name", "")).strip()
    commit_message = str(form.get("commit_message", "")).strip()
    cfg = app_settings.load_settings(paths.repo_root)
    preferred_branch = str(cfg.get("preferred_config_branch", "") or "")

    target_branch = branch_name or preferred_branch
    if not target_branch:
        return HTMLResponse(
            "<div class='flash error'>Commit Only failed: branch_name is required (or set UI target branch first).</div>",
            status_code=200,
        )

    try:
        result = git_ops.prepare_commit(
            paths.repo_root,
            tracked_files=_git_tracked_paths(paths),
            branch_name=target_branch,
            preferred_branch=preferred_branch or None,
            fallback_tz=str(cfg.get("timezone", app_settings.DEFAULT_TIMEZONE)),
            commit_message=commit_message or None,
            require_existing_branch=True,
        )
        app_settings.save_preferred_config_branch(paths.repo_root, str(result.get("branch", "")))
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Commit Only failed: {exc}</div>", status_code=200)

    files_html = "".join(f"<li><code>{f}</code></li>" for f in result.get("changed_files", []))
    next_cmds = "".join(f"<li><code>{c}</code></li>" for c in result.get("next_commands", []))
    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Committed on existing branch <code>{result['branch']}</code> at <code>{result['commit_sha']}</code>."
            "</div>"
            "<div class='panel'>"
            "<h4>Changed Files</h4>"
            f"<ul class='simple-list'>{files_html or '<li>-</li>'}</ul>"
            "<h4>Next Commands</h4>"
            f"<ul class='simple-list'>{next_cmds or '<li>-</li>'}</ul>"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/create-pr")
async def git_create_pr(request: Request):
    paths = _paths()
    form = await request.form()
    head_branch = str(form.get("head_branch", "")).strip()
    base_branch = str(form.get("base_branch", "main")).strip() or "main"
    pr_title = str(form.get("pr_title", "")).strip()
    pr_body = str(form.get("pr_body", ""))
    use_fill = str(form.get("use_fill", "")).strip().lower() in {"1", "true", "on", "yes"}

    if not head_branch:
        head_branch = app_settings.get_preferred_config_branch(paths.repo_root)

    try:
        created = git_ops.create_pr(
            paths.repo_root,
            head_branch=head_branch,
            base_branch=base_branch,
            title=pr_title,
            body=pr_body,
            use_fill=use_fill,
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            (
                "<div class='flash error'>"
                f"Create PR failed: {exc}<br/>"
                "Go to <code>Settings -> Connections -> GitHub</code> and connect via browser OAuth "
                "(<code>gh auth login --web</code>), then retry."
                "</div>"
            ),
            status_code=200,
        )

    url = created.get("url", "")
    link = f"<a href='{url}' target='_blank' rel='noreferrer'>{url}</a>" if url else "(URL not returned by gh)"
    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"PR created for <code>{created['head']}</code> -> <code>{created['base']}</code>.<br/>"
            f"{link}"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/delete-pr")
async def git_delete_pr(request: Request):
    paths = _paths()
    form = await request.form()
    pr_number_raw = str(form.get("pr_number", "")).strip()
    delete_branch = str(form.get("delete_branch", "")).strip().lower() in {"1", "true", "on", "yes"}

    try:
        pr_number = int(pr_number_raw)
    except ValueError:
        return HTMLResponse("<div class='flash error'>Delete PR failed: pr_number must be an integer.</div>", status_code=200)

    try:
        result = git_ops.close_pr(paths.repo_root, pr_number=pr_number, delete_branch=delete_branch)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            (
                "<div class='flash error'>"
                f"Delete PR failed: {exc}<br/>"
                "Go to <code>Settings -> Connections -> GitHub</code> and connect via browser OAuth "
                "(<code>gh auth login --web</code>), then retry."
                "</div>"
            ),
            status_code=200,
        )

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"PR <code>#{result['number']}</code> closed."
            + (" Related branch delete requested." if result.get("delete_branch") else "")
            + "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/delete-branch")
async def git_delete_branch(request: Request):
    paths = _paths()
    form = await request.form()
    branch_name = str(form.get("branch_name", "")).strip()
    remote_name = str(form.get("remote_name", "origin")).strip() or "origin"
    delete_local = str(form.get("delete_local", "")).strip().lower() in {"1", "true", "on", "yes"}
    delete_remote = str(form.get("delete_remote", "")).strip().lower() in {"1", "true", "on", "yes"}

    try:
        result = git_ops.delete_branch(
            paths.repo_root,
            branch_name=branch_name,
            delete_local=delete_local,
            delete_remote=delete_remote,
            remote_name=remote_name,
        )
        preferred = app_settings.get_preferred_config_branch(paths.repo_root)
        if preferred and preferred == branch_name:
            app_settings.save_preferred_config_branch(paths.repo_root, "")
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Delete branch failed: {exc}</div>", status_code=200)

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Branch <code>{result['branch']}</code> delete complete. "
            f"local_deleted={result['local_deleted']}, remote_deleted={result['remote_deleted']}."
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/git-commits/push")
async def git_push_branch(request: Request):
    paths = _paths()
    form = await request.form()
    branch_name = str(form.get("branch_name", "")).strip()
    remote_name = str(form.get("remote_name", "origin")).strip() or "origin"
    set_upstream = str(form.get("set_upstream", "")).strip().lower() in {"1", "true", "on", "yes"}
    preferred_branch = app_settings.get_preferred_config_branch(paths.repo_root)

    try:
        result = git_ops.push_branch(
            paths.repo_root,
            branch_name=branch_name or preferred_branch or None,
            remote_name=remote_name,
            set_upstream=set_upstream,
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>Push failed: {exc}</div>", status_code=200)

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Pushed <code>{result['branch']}</code> to <code>{result['remote']}</code>."
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.get("/machines")
@router.get("/config-management/machines")
@router.get("/features/config-management/machines")
def machines_page(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    return templates.TemplateResponse(
        "machines.html",
        _ctx(
            request,
            page_title="Machines",
            machines=sorted(machines.items(), key=lambda x: x[0]),
        ),
    )


@router.get("/operations")
@router.get("/config-management/operations")
@router.get("/features/config-management/operations")
def operations_page(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    operations = bundle.operations_doc.get("operations", {})
    machines = sorted(bundle.machines_doc.get("machines", {}).keys())
    return templates.TemplateResponse(
        "operations.html",
        _ctx(
            request,
            page_title="Operations",
            operations=sorted(operations.items(), key=lambda x: x[0]),
            machine_ids=machines,
        ),
    )


@router.get("/env-rules")
@router.get("/config-management/env-rules")
@router.get("/features/config-management/env-rules")
@router.get("/rules")
@router.get("/config-management/rules")
@router.get("/features/config-management/rules")
def env_rules_page(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    rules = bundle.rules_doc.get("rules", {})
    stage_ids = sorted(validators.available_setup_ids(paths.repo_root))
    rule_ids = sorted(rules.keys()) if isinstance(rules, dict) else []
    all_setup_ids = sorted(set(stage_ids) | set(rule_ids))
    env_rule_rows: List[Dict[str, Any]] = []
    for setup_id in all_setup_ids:
        raw_rule = rules.get(setup_id, {}) if isinstance(rules, dict) else {}
        rule_payload = raw_rule if isinstance(raw_rule, dict) else {}
        env_rule_rows.append(
            {
                "setup_id": setup_id,
                "rule": {
                    "requires_confirmation": bool(rule_payload.get("requires_confirmation", False)),
                    "allowed_environments": rule_payload.get("allowed_environments", []) or [],
                },
                "is_explicit": setup_id in rules if isinstance(rules, dict) else False,
            }
        )
    return templates.TemplateResponse(
        "env_rules.html",
        _ctx(
            request,
            page_title="Env Rules",
            env_rule_rows=env_rule_rows,
        ),
    )


@router.get("/config-management/readme/{topic}")
@router.get("/features/config-management/readme/{topic}")
def config_readme_page(request: Request, topic: str):
    readme = _config_readme(str(topic).strip().lower())
    if not readme:
        return RedirectResponse(url="/config-management", status_code=307)
    return templates.TemplateResponse(
        "config_readme.html",
        _ctx(
            request,
            page_title=readme.get("title", "Config README"),
            readme=readme,
        ),
    )


@router.get("/config-management/source-of-truth")
@router.get("/features/config-management/source-of-truth")
def source_of_truth_page(request: Request):
    paths = _paths()
    files = [str(paths.machines_path.relative_to(paths.repo_root))]
    if paths.operations_path.exists():
        files.append(str(paths.operations_path.relative_to(paths.repo_root)))
    if paths.rules_path.exists():
        files.append(str(paths.rules_path.relative_to(paths.repo_root)))
    return templates.TemplateResponse(
        "source_of_truth.html",
        _ctx(
            request,
            page_title="Source of Truth for Config",
            files=files,
        ),
    )


@router.get("/config-management/backups")
@router.get("/features/config-management/backups")
def backups_page(
    request: Request,
    label_q: str = "",
    date: str = "",
    date_from: str = "",
    date_to: str = "",
    last_n: str = "",
):
    paths = _paths()
    timezone_name = app_settings.get_timezone(paths.repo_root)
    parsed_last_n = None
    filter_errors: List[str] = []

    last_n_value = (last_n or "").strip()
    if last_n_value:
        try:
            parsed_last_n = int(last_n_value)
            if parsed_last_n <= 0:
                raise ValueError("last_n must be greater than 0")
        except ValueError:
            filter_errors.append("last_n must be a positive number (for example: 5, 10, 15).")
            parsed_last_n = None

    try:
        records = backups.list_backups(
            paths,
            label_query=label_q,
            date_exact=date,
            date_from=date_from,
            date_to=date_to,
            last_n=parsed_last_n,
            tz_name=timezone_name,
        )
    except Exception as exc:  # noqa: BLE001
        filter_errors.append(str(exc))
        records = backups.list_backups(paths, tz_name=timezone_name)

    rendered_records: List[Dict[str, Any]] = []
    for item in records:
        enriched = dict(item)
        enriched["created_at_display"] = app_settings.format_iso_datetime(
            str(item.get("created_at", "")),
            timezone_name,
        )
        rendered_records.append(enriched)

    return templates.TemplateResponse(
        "backups.html",
        _ctx(
            request,
            page_title="Config Backups",
            backups=rendered_records,
            filter_errors=filter_errors,
            backup_filters={
                "label_q": label_q,
                "date": date,
                "date_from": date_from,
                "date_to": date_to,
                "last_n": last_n_value,
            },
            backup_timezone=timezone_name,
        ),
    )


@router.post("/config-management/backups/create")
async def create_backup(request: Request):
    paths = _paths()
    timezone_name = app_settings.get_timezone(paths.repo_root)
    form = await request.form()
    label = str(form.get("label", "")).strip()
    remark = str(form.get("remark", "")).strip()
    try:
        meta = backups.create_backup(paths, label=label, remark=remark, tz_name=timezone_name)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<div class='flash error'>Backup failed: {exc}</div>",
            status_code=200,
        )

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Backup created: <code>{meta.get('backup_id', '')}</code>"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/backups/restore")
async def restore_backup(request: Request):
    paths = _paths()
    form = await request.form()
    backup_id = str(form.get("backup_id", "")).strip()
    try:
        restored = backups.restore_backup(paths, backup_id=backup_id)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<div class='flash error'>Restore failed: {exc}</div>",
            status_code=200,
        )

    # Publish realtime change so open views can refresh after restore.
    published = bus.publish("config_changed", {"files": restored["restored_files"], "source": "backup_restore"})

    bundle = config_store.load_bundle(paths)
    validation_errors = validators.validate_bundle(bundle, paths.repo_root)
    if validation_errors:
        return HTMLResponse(
            (
                "<div class='flash warn'>"
                f"Backup <code>{backup_id}</code> restored, but validation has issues: "
                f"{len(validation_errors)}"
                "</div>"
            ),
            headers={"HX-Refresh": "true", "X-Realtime-Version": str(published.version)},
        )

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Backup <code>{backup_id}</code> restored successfully."
            "</div>"
        ),
        headers={"HX-Refresh": "true", "X-Realtime-Version": str(published.version)},
    )


@router.post("/config-management/backups/delete")
async def delete_backup(request: Request):
    paths = _paths()
    form = await request.form()
    backup_id = str(form.get("backup_id", "")).strip()
    try:
        deleted = backups.delete_backup(paths, backup_id=backup_id)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<div class='flash error'>Delete failed: {exc}</div>",
            status_code=200,
        )

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Deleted backup <code>{deleted['backup_id']}</code> "
            f"from <code>{deleted['removed_path']}</code>."
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.post("/config-management/backups/cleanup")
async def cleanup_backups(request: Request):
    paths = _paths()
    form = await request.form()
    keep_last_n_raw = str(form.get("keep_last_n", "")).strip() or "5"

    try:
        keep_last_n = int(keep_last_n_raw)
    except ValueError:
        return HTMLResponse(
            "<div class='flash error'>Cleanup failed: keep_last_n must be an integer.</div>",
            status_code=200,
        )

    if keep_last_n <= 0:
        return HTMLResponse(
            "<div class='flash error'>Cleanup failed: keep_last_n must be greater than 0.</div>",
            status_code=200,
        )

    try:
        result = backups.cleanup_backups_before_last_n(paths, keep_last_n=keep_last_n)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<div class='flash error'>Cleanup failed: {exc}</div>",
            status_code=200,
        )

    deleted_ids = result.get("deleted_backup_ids", []) or []
    deleted_html = (
        "<ul class='simple-list'>"
        + "".join(f"<li><code>{x}</code></li>" for x in deleted_ids)
        + "</ul>"
    ) if deleted_ids else "<p class='muted'>No backups were removed.</p>"

    return HTMLResponse(
        (
            "<div class='flash success'>"
            f"Backup cleanup complete. Kept last <code>{result.get('keep_last_n')}</code>, "
            f"deleted <code>{result.get('deleted_count')}</code> older backup(s)."
            "</div>"
            "<div class='panel'>"
            f"<p>Before: <code>{result.get('total_before')}</code> | After: <code>{result.get('total_after')}</code></p>"
            "<h4>Deleted Backup IDs</h4>"
            f"{deleted_html}"
            "</div>"
        ),
        headers={"HX-Refresh": "true"},
    )


@router.get("/machines/form")
def machine_form(request: Request, machine_id: Optional[str] = None):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    existing = machines.get(machine_id, {}) if machine_id else {}
    stage_ids = sorted(validators.available_setup_ids(paths.repo_root))

    return templates.TemplateResponse(
        "partials/machine_form.html",
        _ctx(
            request,
            machine_id=machine_id or "",
            machine=existing,
            stage_ids=stage_ids,
            mode="edit" if machine_id else "create",
        ),
    )


@router.get("/machines/access")
def machine_access_form(request: Request, machine_id: str):
    machine_key = str(machine_id or "").strip()
    if not machine_key:
        return HTMLResponse("<div class='flash error'>machine_id is required.</div>", status_code=400)

    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    machine = machines.get(machine_key, {})
    if not isinstance(machine, dict) or not machine:
        return HTMLResponse(f"<div class='flash error'>Machine not found: {machine_key}</div>", status_code=404)

    return templates.TemplateResponse(
        "partials/machine_access_form.html",
        _ctx(
            request,
            machine_id=machine_key,
            machine=machine,
        ),
    )


@router.post("/machines/access/preview")
async def machine_access_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)

    try:
        parsed = _machine_access_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(parsed["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {parsed['machine_id']}")
        _apply_machine_access_payload(machine, parsed)
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.machines_doc)
    diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Machine Access Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/machines/access/save")
async def machine_access_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)

    try:
        parsed = _machine_access_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(parsed["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {parsed['machine_id']}")
        _apply_machine_access_payload(machine, parsed)
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Access Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.machines_doc)
        diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Access Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["machines"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Machine Access Save",
                errors=[f"Failed to write vm-configs/vm-machines.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse(
        "<div class='flash success'>Machine access details saved.</div>",
        headers={"HX-Refresh": "true"},
    )


@router.get("/machines/notes")
def machine_notes_form(request: Request, machine_id: str):
    machine_key = str(machine_id or "").strip()
    if not machine_key:
        return HTMLResponse("<div class='flash error'>machine_id is required.</div>", status_code=400)

    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    machine = machines.get(machine_key, {})
    if not isinstance(machine, dict) or not machine:
        return HTMLResponse(f"<div class='flash error'>Machine not found: {machine_key}</div>", status_code=404)

    notes_md = str(machine.get("notes", "") or "")
    return templates.TemplateResponse(
        "partials/machine_notes_form.html",
        _ctx(
            request,
            machine_id=machine_key,
            notes_md=notes_md,
            notes_rendered=_render_markdown_safe(notes_md),
        ),
    )


@router.post("/machines/notes/render")
async def machine_notes_render(request: Request):
    form = await request.form()
    payload = _machine_notes_payload_from_form(dict(form))
    rendered = _render_markdown_safe(payload["notes"])
    return HTMLResponse(
        (
            "<div class='panel markdown-preview'>"
            "<h5>Markdown Preview</h5>"
            f"<div class='markdown-body'>{rendered}</div>"
            "</div>"
        ),
        status_code=200,
    )


@router.post("/machines/notes/preview")
async def machine_notes_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)
    try:
        payload = _machine_notes_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(payload["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {payload['machine_id']}")
        machine["notes"] = payload["notes"]
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.machines_doc)
    diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Machine Notes Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/machines/notes/save")
async def machine_notes_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)
    try:
        payload = _machine_notes_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(payload["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {payload['machine_id']}")
        machine["notes"] = payload["notes"]
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Notes Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.machines_doc)
        diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Notes Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["machines"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Machine Notes Save",
                errors=[f"Failed to write vm-configs/vm-machines.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse(
        "<div class='flash success'>Machine notes saved.</div>",
        headers={"HX-Refresh": "true"},
    )


@router.get("/machines/current-setup-checklist")
def machine_current_setup_checklist_form(request: Request, machine_id: str):
    machine_key = str(machine_id or "").strip()
    if not machine_key:
        return HTMLResponse("<div class='flash error'>machine_id is required.</div>", status_code=400)

    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    machine = machines.get(machine_key, {})
    if not isinstance(machine, dict) or not machine:
        return HTMLResponse(f"<div class='flash error'>Machine not found: {machine_key}</div>", status_code=404)

    enabled_setups_raw = machine.get("enabled_setups", machine.get("enabled_stages", []))
    enabled_setups = [str(x) for x in enabled_setups_raw] if isinstance(enabled_setups_raw, list) else []
    current_setup_checklist_raw = machine.get("current_setup_checklist", [])
    current_setup_checklist = [str(x) for x in current_setup_checklist_raw] if isinstance(current_setup_checklist_raw, list) else []

    return templates.TemplateResponse(
        "partials/machine_current_setup_checklist_form.html",
        _ctx(
            request,
            machine_id=machine_key,
            enabled_setups=enabled_setups,
            current_setup_checklist=current_setup_checklist,
        ),
    )


@router.post("/machines/current-setup-checklist/preview")
async def machine_current_setup_checklist_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)
    try:
        payload = _machine_setup_checklist_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(payload["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {payload['machine_id']}")
        machine["current_setup_checklist"] = payload["current_setup_checklist"]
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.machines_doc)
    diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Current Setup Checklist Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/machines/current-setup-checklist/save")
async def machine_current_setup_checklist_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)
    try:
        payload = _machine_setup_checklist_payload_from_form(form_data)
        machines = candidate.machines_doc.get("machines", {})
        machine = machines.get(payload["machine_id"], {})
        if not isinstance(machine, dict) or not machine:
            raise ValueError(f"Machine not found: {payload['machine_id']}")
        machine["current_setup_checklist"] = payload["current_setup_checklist"]
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Current Setup Checklist Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.machines_doc)
        diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Current Setup Checklist Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["machines"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Current Setup Checklist Save",
                errors=[f"Failed to write vm-configs/vm-machines.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse(
        "<div class='flash success'>Current setup checklist saved.</div>",
        headers={"HX-Refresh": "true"},
    )


@router.get("/machines/setup-config")
def machine_setup_config_preview(request: Request, machine_id: str, setup_id: str):
    machine_key = str(machine_id or "").strip()
    setup_key = str(setup_id or "").strip()
    if not machine_key or not setup_key:
        return HTMLResponse("<div class='flash error'>machine_id and setup_id are required.</div>", status_code=400)

    paths = _paths()
    bundle = config_store.load_bundle(paths)
    machines = bundle.machines_doc.get("machines", {})
    machine = machines.get(machine_key, {})
    if not isinstance(machine, dict) or not machine:
        return HTMLResponse(f"<div class='flash error'>Machine not found: {machine_key}</div>", status_code=404)

    try:
        setup_meta = _load_setup_meta(paths.repo_root, setup_key)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>{exc}</div>", status_code=404)

    enabled_setups_raw = machine.get("enabled_setups", machine.get("enabled_stages", []))
    enabled_setups = [str(x) for x in enabled_setups_raw] if isinstance(enabled_setups_raw, list) else []
    is_enabled_for_machine = setup_key in enabled_setups

    supports_modes_raw = setup_meta.get("supports_exec_modes", [])
    supports_modes = [str(x) for x in supports_modes_raw] if isinstance(supports_modes_raw, list) else []
    machine_exec_modes_runtime = _machine_runtime_exec_modes(machine.get("exec_mode"))
    exec_mode_compatible = (not supports_modes) or any(mode in supports_modes for mode in machine_exec_modes_runtime)

    allowed_target_types_raw = setup_meta.get("allowed_target_types", [])
    allowed_target_types = [str(x) for x in allowed_target_types_raw] if isinstance(allowed_target_types_raw, list) else []
    machine_target_runtime = _machine_runtime_target_type(machine)
    target_type_compatible = (not allowed_target_types) or (machine_target_runtime in allowed_target_types)

    required_params_raw = setup_meta.get("required_params", [])
    required_params = [str(x) for x in required_params_raw] if isinstance(required_params_raw, list) else []
    optional_params_raw = setup_meta.get("optional_params", [])
    optional_params = [str(x) for x in optional_params_raw] if isinstance(optional_params_raw, list) else []

    machine_params = machine.get("params", {})
    machine_param_keys = set(machine_params.keys()) if isinstance(machine_params, dict) else set()
    machine_defaults_obj = machine.get("defaults", {})
    machine_setup_defaults: Dict[str, Any] = {}
    if isinstance(machine_defaults_obj, dict):
        by_setup = machine_defaults_obj.get("setup_defaults", {})
        if isinstance(by_setup, dict):
            per_setup = by_setup.get(setup_key, {})
            if isinstance(per_setup, dict):
                machine_setup_defaults = {str(k): v for k, v in per_setup.items()}

    operations = bundle.operations_doc.get("operations", {})
    operation_refs: List[str] = []
    operation_details: List[Dict[str, Any]] = []
    operation_param_keys = set()
    operation_param_map: Dict[str, Dict[str, Any]] = {}
    if isinstance(operations, dict):
        for op_id, op in operations.items():
            if not isinstance(op, dict):
                continue
            if str(op.get("machine", "")).strip() != machine_key:
                continue
            op_setups = op.get("setups", op.get("default_stages", []))
            if isinstance(op_setups, list) and setup_key in [str(x) for x in op_setups]:
                operation_refs.append(str(op_id))
                op_params = op.get("params", op.get("default_params", {}))
                if isinstance(op_params, dict):
                    operation_param_map[str(op_id)] = {str(k): v for k, v in op_params.items()}
                    operation_param_keys.update(str(k) for k in op_params.keys())
                else:
                    operation_param_map[str(op_id)] = {}
    operation_refs.sort()
    operation_details = [
        {"operation_id": op_id, "params": operation_param_map.get(op_id, {})}
        for op_id in operation_refs
    ]

    required_from_machine = [p for p in required_params if p in machine_param_keys]
    required_from_operations = [p for p in required_params if p not in machine_param_keys and p in operation_param_keys]
    missing_required = [p for p in required_params if p not in machine_param_keys and p not in operation_param_keys]

    setup_param_meta = _extract_stage_param_meta(paths.repo_root, setup_key)
    setup_defaults = {k: v.get("default") for k, v in setup_param_meta.items() if isinstance(v, dict)}
    expected_param_order: List[str] = []
    for p in required_params + optional_params + sorted(setup_param_meta.keys()):
        if p not in expected_param_order:
            expected_param_order.append(p)

    param_resolution_rows: List[Dict[str, Any]] = []
    for param_name in expected_param_order:
        has_stage_default = param_name in setup_defaults
        stage_default = setup_defaults.get(param_name)
        machine_has = param_name in machine_param_keys
        machine_value = machine_params.get(param_name) if machine_has else None

        op_values: List[Dict[str, Any]] = []
        for op_id in operation_refs:
            op_params = operation_param_map.get(op_id, {})
            if param_name in op_params:
                op_values.append({"operation_id": op_id, "value": op_params[param_name]})

        if machine_has:
            effective_source = "machine.params"
            effective_value = machine_value
            effective_note = ""
            has_effective_value = True
        elif op_values:
            unique_values = {json.dumps(x["value"], sort_keys=True) for x in op_values}
            effective_source = "operation.params"
            if len(unique_values) == 1:
                effective_value = op_values[0]["value"]
                effective_note = ""
            else:
                effective_value = None
                effective_note = "Different operation overrides exist for this param."
            has_effective_value = len(unique_values) == 1
        elif has_stage_default:
            effective_source = "stage_default"
            effective_value = stage_default
            effective_note = ""
            has_effective_value = True
        else:
            effective_source = "unset"
            effective_value = None
            effective_note = "No value found in machine, operations, or known stage defaults."
            has_effective_value = False

        param_resolution_rows.append(
            {
                "name": param_name,
                "has_stage_default": has_stage_default,
                "stage_default": stage_default,
                "machine_has": machine_has,
                "machine_value": machine_value,
                "operation_values": op_values,
                "effective_source": effective_source,
                "has_effective_value": has_effective_value,
                "effective_value": effective_value,
                "effective_note": effective_note,
            }
        )

    param_help_map = _setup_param_help(setup_key, expected_param_order)
    dynamic_editor_fields: List[Dict[str, Any]] = []
    for row in param_resolution_rows:
        field_name = str(row["name"])
        default_value = row.get("stage_default")
        field_meta = setup_param_meta.get(field_name, {})
        input_type = _param_input_type(field_name, field_meta, default_value)
        if row.get("machine_has"):
            edit_value = row.get("machine_value")
        elif row.get("has_stage_default"):
            edit_value = default_value
        elif row.get("has_effective_value"):
            edit_value = row.get("effective_value")
        else:
            edit_value = ""
        if input_type == "bool" and edit_value in {"", None}:
            edit_value = bool(default_value) if isinstance(default_value, bool) else False

        display_default_value = machine_setup_defaults.get(field_name, default_value)
        dynamic_editor_fields.append(
            {
                "name": field_name,
                "input_type": input_type,
                "edit_value": edit_value,
                "default_value": default_value,
                "display_default_value": display_default_value,
                "effective_source": row.get("effective_source", "unset"),
                "effective_note": row.get("effective_note", ""),
                "help_lines": param_help_map.get(field_name, []),
            }
        )

    field_by_name: Dict[str, Dict[str, Any]] = {
        str(f.get("name", "")): f for f in dynamic_editor_fields if str(f.get("name", ""))
    }
    dynamic_editor_rows: List[Dict[str, Any]] = []
    consumed: set[str] = set()
    for name in expected_param_order:
        if name in consumed:
            continue
        field = field_by_name.get(name)
        if not field:
            continue

        # Render version pins as a column of their base option row.
        if name.endswith("_version_pin"):
            base_name = _base_for_version_pin(name, field_by_name)
            if base_name:
                consumed.add(name)
                continue

        version_pin_field: Optional[Dict[str, Any]] = None
        if not name.endswith("_version_pin"):
            vp_name = _version_pin_for_base(name, field_by_name)
            if vp_name and vp_name in field_by_name:
                version_pin_field = field_by_name[vp_name]
                consumed.add(vp_name)

        consumed.add(name)
        dynamic_editor_rows.append(
            {
                "field": field,
                "version_pin_field": version_pin_field,
            }
        )

    has_any_version_pin = any(row.get("version_pin_field") is not None for row in dynamic_editor_rows)
    has_any_bool = any(str(row.get("field", {}).get("input_type", "")).strip() == "bool" for row in dynamic_editor_rows)
    has_any_non_bool = any(str(row.get("field", {}).get("input_type", "")).strip() != "bool" for row in dynamic_editor_rows)
    if has_any_bool and not has_any_non_bool:
        value_label = "enabled"
        default_value_label = "default_enabled"
    elif has_any_non_bool and not has_any_bool:
        value_label = "value"
        default_value_label = "default_value"
    else:
        value_label = "value / enabled"
        default_value_label = "default"

    dynamic_table_meta = {
        "show_version_pin_columns": has_any_version_pin,
        "value_label": value_label,
        "default_value_label": default_value_label,
    }

    expected_param_set = set(expected_param_order)
    extra_machine_params = sorted([k for k in machine_param_keys if k not in expected_param_set])
    extra_operation_params = sorted([k for k in operation_param_keys if k not in expected_param_set])
    setup_dynamic_notes = _setup_dynamic_notes(setup_key)

    rules = bundle.rules_doc.get("rules", {})
    raw_rule = rules.get(setup_key, {}) if isinstance(rules, dict) else {}
    rule = raw_rule if isinstance(raw_rule, dict) else {}
    allowed_envs_raw = rule.get("allowed_environments", [])
    allowed_envs = [str(x) for x in allowed_envs_raw] if isinstance(allowed_envs_raw, list) else []
    machine_env = str(machine.get("env", machine.get("environment", ""))).strip()
    env_allowed = (not allowed_envs) or (machine_env in allowed_envs)

    return templates.TemplateResponse(
        "partials/machine_setup_config_preview.html",
        _ctx(
            request,
            machine_id=machine_key,
            setup_id=setup_key,
            machine=machine,
            setup_meta=setup_meta,
            is_enabled_for_machine=is_enabled_for_machine,
            supports_modes=supports_modes,
            machine_exec_runtime=",".join(machine_exec_modes_runtime),
            exec_mode_compatible=exec_mode_compatible,
            allowed_target_types=allowed_target_types,
            machine_target_runtime=machine_target_runtime,
            target_type_compatible=target_type_compatible,
            required_params=required_params,
            optional_params=optional_params,
            required_from_machine=required_from_machine,
            required_from_operations=required_from_operations,
            missing_required=missing_required,
            operation_refs=operation_refs,
            operation_details=operation_details,
            rule=rule,
            allowed_envs=allowed_envs,
            machine_env=machine_env,
            env_allowed=env_allowed,
            setup_defaults=setup_defaults,
            param_resolution_rows=param_resolution_rows,
            extra_machine_params=extra_machine_params,
            extra_operation_params=extra_operation_params,
            setup_dynamic_notes=setup_dynamic_notes,
            dynamic_editor_fields=dynamic_editor_fields,
            dynamic_editor_rows=dynamic_editor_rows,
            dynamic_table_meta=dynamic_table_meta,
            param_help_map=param_help_map,
            setup_param_meta=setup_param_meta,
            machine_setup_defaults=machine_setup_defaults,
        ),
    )


@router.post("/machines/setup-config/save")
async def machine_setup_config_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    before_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    machine_key = str(form.get("machine_id", "")).strip()
    setup_key = str(form.get("setup_id", "")).strip()
    if not machine_key or not setup_key:
        return HTMLResponse(
            "<div class='flash error'>machine_id and setup_id are required.</div>",
            status_code=400,
        )

    machines = candidate.machines_doc.get("machines", {})
    machine = machines.get(machine_key, {})
    if not isinstance(machine, dict) or not machine:
        return HTMLResponse(
            f"<div class='flash error'>Machine not found: {machine_key}</div>",
            status_code=404,
        )

    try:
        setup_meta = _load_setup_meta(paths.repo_root, setup_key)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(f"<div class='flash error'>{exc}</div>", status_code=404)

    required_params_raw = setup_meta.get("required_params", [])
    required_params = [str(x) for x in required_params_raw] if isinstance(required_params_raw, list) else []
    optional_params_raw = setup_meta.get("optional_params", [])
    optional_params = [str(x) for x in optional_params_raw] if isinstance(optional_params_raw, list) else []
    setup_param_meta = _extract_stage_param_meta(paths.repo_root, setup_key)
    editable_params = []
    for p in required_params + optional_params + sorted(setup_param_meta.keys()):
        if p not in editable_params:
            editable_params.append(p)

    setup_defaults = {k: v.get("default") for k, v in setup_param_meta.items() if isinstance(v, dict)}
    params = machine.get("params", {})
    if not isinstance(params, dict):
        params = {}
        machine["params"] = params

    parsed_values: Dict[str, Any] = {}
    for param_name in editable_params:
        key = f"dynamic__{param_name}"
        if key not in form:
            continue
        raw_value = form.get(key)
        input_type = _param_input_type(param_name, setup_param_meta.get(param_name), setup_defaults.get(param_name))
        try:
            if input_type == "bool":
                parsed = _parse_bool_text(raw_value, key)
            else:
                parsed = str(raw_value or "").strip()
        except ValueError as exc:
            return HTMLResponse(f"<div class='flash error'>{exc}</div>", status_code=400)
        parsed_values[param_name] = parsed

    apply_defaults = _bool_from_form(dict(form), "apply_defaults", False)
    changed_count = 0
    for param_name, parsed in parsed_values.items():
        if params.get(param_name) != parsed:
            params[param_name] = parsed
            changed_count += 1

    defaults_changed = 0
    if apply_defaults:
        defaults_obj = machine.get("defaults", {})
        if not isinstance(defaults_obj, dict):
            defaults_obj = {}
        by_setup = defaults_obj.get("setup_defaults", {})
        if not isinstance(by_setup, dict):
            by_setup = {}

        existing = by_setup.get(setup_key, {})
        if not isinstance(existing, dict):
            existing = {}

        new_default_map: Dict[str, Any] = {}
        for param_name in editable_params:
            if param_name in parsed_values:
                new_default_map[param_name] = parsed_values[param_name]
            elif param_name in existing:
                new_default_map[param_name] = existing[param_name]
            elif param_name in setup_defaults:
                new_default_map[param_name] = setup_defaults[param_name]

        if existing != new_default_map:
            by_setup[setup_key] = new_default_map
            defaults_obj["setup_defaults"] = by_setup
            machine["defaults"] = defaults_obj
            defaults_changed = 1

    after_errors = validators.validate_bundle(candidate, paths.repo_root)
    introduced = _introduced_errors(before_errors, after_errors)
    if introduced:
        items = "".join(f"<li>{e}</li>" for e in introduced)
        return HTMLResponse(
            "<div class='flash error'><strong>Cannot save due to new validation errors:</strong>"
            f"<ul class='simple-list'>{items}</ul></div>",
            status_code=400,
        )

    if changed_count == 0 and defaults_changed == 0:
        return HTMLResponse("<div class='flash warn'>No dynamic option changes detected.</div>")

    try:
        config_store.save_bundle(paths, candidate, ["machines"])
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<div class='flash error'>Failed to save vm-configs/vm-machines.yaml: {exc}</div>",
            status_code=500,
        )

    success_message = (
        "<div class='flash success'>"
        f"Saved {changed_count} dynamic option(s) for <code>{machine_key}</code> / <code>{setup_key}</code>."
        f"{' Defaults updated.' if defaults_changed else ''}"
        "</div>"
    )
    return HTMLResponse(success_message, headers={"HX-Refresh": "true"})


@router.post("/machines/preview")
async def machine_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)

    try:
        parsed = _machine_payload_from_form(form_data)
        config_store.upsert_machine(
            candidate,
            machine_id=parsed["machine_id"],
            machine_payload=parsed["payload"],
            original_machine_id=parsed["original_machine_id"],
        )
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.machines_doc)
    diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Machine Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/machines/save")
async def machine_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)

    try:
        parsed = _machine_payload_from_form(form_data)
        config_store.upsert_machine(
            candidate,
            machine_id=parsed["machine_id"],
            machine_payload=parsed["payload"],
            original_machine_id=parsed["original_machine_id"],
        )
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.machines_doc)
        diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["machines"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Machine Save",
                errors=[f"Failed to write vm-configs/vm-machines.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse("<div class='flash success'>Machine config saved.</div>", headers={"HX-Refresh": "true"})


@router.get("/operations/form")
def operation_form(request: Request, operation_id: Optional[str] = None):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    operations = bundle.operations_doc.get("operations", {})
    existing = operations.get(operation_id, {}) if operation_id else {}
    machine_ids = sorted(bundle.machines_doc.get("machines", {}).keys())
    stage_ids = sorted(validators.available_setup_ids(paths.repo_root))

    return templates.TemplateResponse(
        "partials/operation_form.html",
        _ctx(
            request,
            operation_id=operation_id or "",
            operation=existing,
            machine_ids=machine_ids,
            stage_ids=stage_ids,
            mode="edit" if operation_id else "create",
        ),
    )


@router.post("/operations/preview")
async def operation_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)
    try:
        parsed = _operation_payload_from_form(form_data)
        config_store.upsert_operation(
            candidate,
            operation_id=parsed["operation_id"],
            operation_payload=parsed["payload"],
            original_operation_id=parsed["original_operation_id"],
        )
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.operations_doc)
    diff_text = config_store.render_diff(bundle.operations_text, new_text, "vm-configs/vm-operations.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Operation Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/operations/save")
async def operation_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)

    try:
        parsed = _operation_payload_from_form(form_data)
        config_store.upsert_operation(
            candidate,
            operation_id=parsed["operation_id"],
            operation_payload=parsed["payload"],
            original_operation_id=parsed["original_operation_id"],
        )
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Operation Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.operations_doc)
        diff_text = config_store.render_diff(bundle.operations_text, new_text, "vm-configs/vm-operations.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Operation Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["operations"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Operation Save",
                errors=[f"Failed to write vm-configs/vm-operations.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse("<div class='flash success'>Operation config saved.</div>", headers={"HX-Refresh": "true"})


@router.get("/env-rules/form")
@router.get("/rules/form")
def env_rule_form(request: Request, setup_id: Optional[str] = None):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    rules = bundle.rules_doc.get("rules", {})
    stage_ids = sorted(validators.available_setup_ids(paths.repo_root))
    requested_setup_id = (setup_id or "").strip()
    missing_setup_ids = [sid for sid in stage_ids if sid not in rules]

    # Create mode defaults to first missing setup so users can quickly define coverage.
    if requested_setup_id:
        selected_setup_id = requested_setup_id
    elif missing_setup_ids:
        selected_setup_id = missing_setup_ids[0]
    else:
        selected_setup_id = ""

    is_edit = bool(selected_setup_id and selected_setup_id in rules)
    existing = rules.get(selected_setup_id, {}) if is_edit else {}

    return templates.TemplateResponse(
        "partials/env_rule_form.html",
        _ctx(
            request,
            setup_id=selected_setup_id,
            rule=existing,
            stage_ids=stage_ids,
            mode="edit" if is_edit else "create",
        ),
    )


@router.post("/env-rules/preview")
@router.post("/rules/preview")
async def env_rule_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)
    allowed_envs = _normalize_allowed_environments([str(x) for x in form.getlist("allowed_environments")])

    try:
        parsed = _rule_payload_from_form(form_data, allowed_envs)
        config_store.upsert_rule(
            candidate,
            setup_id=parsed["setup_id"],
            rule_payload=parsed["payload"],
            original_setup_id=parsed["original_setup_id"],
        )
        errors.extend(validators.validate_bundle(candidate, paths.repo_root))
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    new_text = config_store.dump_doc(candidate.rules_doc)
    diff_text = config_store.render_diff(bundle.rules_text, new_text, "vm-configs/vm-env-rules.yaml")
    return templates.TemplateResponse(
        "partials/preview.html",
        _ctx(request, title="Env Rule Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/env-rules/save")
@router.post("/rules/save")
async def env_rule_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)
    allowed_envs = _normalize_allowed_environments([str(x) for x in form.getlist("allowed_environments")])

    try:
        parsed = _rule_payload_from_form(form_data, allowed_envs)
        config_store.upsert_rule(
            candidate,
            setup_id=parsed["setup_id"],
            rule_payload=parsed["payload"],
            original_setup_id=parsed["original_setup_id"],
        )
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Env Rule Save", errors=[str(exc)], diff_text="No changes."),
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    new_errors = _introduced_errors(baseline_errors, errors)
    if new_errors:
        new_text = config_store.dump_doc(candidate.rules_doc)
        diff_text = config_store.render_diff(bundle.rules_text, new_text, "vm-configs/vm-env-rules.yaml")
        messages = ["New validation errors introduced by this change:"] + new_errors
        if baseline_errors:
            messages.append(f"Existing unrelated validation errors in repo: {len(baseline_errors)}")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Env Rule Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["rules"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Env Rule Save",
                errors=[f"Failed to write vm-configs/vm-env-rules.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse("<div class='flash success'>Env rules saved.</div>", headers={"HX-Refresh": "true"})
