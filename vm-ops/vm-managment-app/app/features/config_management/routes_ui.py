#!/usr/bin/env python3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from ...core.app_meta import APP_DISPLAY_NAME
from ...core.realtime_bus import bus
from ..ui_system.service import ui_system_template_dirs
from .services import backups, config_store, git_ops, validators

router = APIRouter(tags=["config-management-ui"])
templates = Jinja2Templates(directory=ui_system_template_dirs())


def _paths() -> config_store.ConfigPaths:
    return config_store.get_paths()


def _ctx(request: Request, **extra: Any) -> Dict[str, Any]:
    backup_status: Dict[str, Any] = {}
    try:
        backup_status = backups.get_backup_status(_paths())
    except Exception:
        backup_status = {}

    return {
        "request": request,
        "app_display_name": APP_DISPLAY_NAME,
        "nav_mode": "config",
        "backup_status": backup_status,
        "config_feature_paths": {
            "dashboard": "/config-management",
            "machines": "/config-management/machines",
            "operations": "/config-management/operations",
            "rules": "/config-management/rules",
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

    payload = {
        "type": str(form.get("target_type", "vm")).strip() or "vm",
        "env": str(form.get("environment", "")).strip(),
        "labels": _split_csv(str(form.get("labels_csv", ""))),
        "groups": _split_csv(str(form.get("groups_csv", ""))),
        "enabled_setups": _split_csv(str(form.get("enabled_setups_csv", ""))),
        "exec_mode": str(form.get("exec_mode", "local")).strip() or "local",
        "repo_path": str(form.get("repo_path", "/opt/vm-codex-v2")).strip() or "/opt/vm-codex-v2",
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


@router.get("/config-management")
@router.get("/features/config-management")
def dashboard(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    status = git_ops.get_status(paths.repo_root)
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
            validation_errors=validation_errors,
        ),
    )


@router.get("/config-management/git-commits")
@router.get("/features/config-management/git-commits")
def git_commits_page(request: Request):
    paths = _paths()
    status = git_ops.get_status(paths.repo_root)
    return templates.TemplateResponse(
        "git_commits.html",
        _ctx(
            request,
            page_title="Branch and Commit",
            git_status=status,
            default_branch=git_ops.default_branch_name(),
            default_message=git_ops.default_commit_message(),
        ),
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


@router.get("/rules")
@router.get("/config-management/rules")
@router.get("/features/config-management/rules")
def rules_page(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    rules = bundle.rules_doc.get("rules", {})
    return templates.TemplateResponse(
        "rules.html",
        _ctx(
            request,
            page_title="Env Rules",
            rules=sorted(rules.items(), key=lambda x: x[0]),
        ),
    )


@router.get("/config-management/source-of-truth")
@router.get("/features/config-management/source-of-truth")
def source_of_truth_page(request: Request):
    paths = _paths()
    return templates.TemplateResponse(
        "source_of_truth.html",
        _ctx(
            request,
            page_title="Source of Truth for Config",
            files=[
                str(paths.machines_path.relative_to(paths.repo_root)),
                str(paths.operations_path.relative_to(paths.repo_root)),
                str(paths.rules_path.relative_to(paths.repo_root)),
            ],
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
        )
    except Exception as exc:  # noqa: BLE001
        filter_errors.append(str(exc))
        records = backups.list_backups(paths)

    return templates.TemplateResponse(
        "backups.html",
        _ctx(
            request,
            page_title="Config Backups",
            backups=records,
            filter_errors=filter_errors,
            backup_filters={
                "label_q": label_q,
                "date": date,
                "date_from": date_from,
                "date_to": date_to,
                "last_n": last_n_value,
            },
        ),
    )


@router.post("/config-management/backups/create")
async def create_backup(request: Request):
    paths = _paths()
    form = await request.form()
    label = str(form.get("label", "")).strip()
    remark = str(form.get("remark", "")).strip()
    try:
        meta = backups.create_backup(paths, label=label, remark=remark)
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


@router.get("/rules/form")
def rule_form(request: Request, setup_id: Optional[str] = None):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    rules = bundle.rules_doc.get("rules", {})
    existing = rules.get(setup_id, {}) if setup_id else {}
    stage_ids = sorted(validators.available_setup_ids(paths.repo_root))

    return templates.TemplateResponse(
        "partials/rule_form.html",
        _ctx(
            request,
            setup_id=setup_id or "",
            rule=existing,
            stage_ids=stage_ids,
            mode="edit" if setup_id else "create",
        ),
    )


@router.post("/rules/preview")
async def rule_preview(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    errors: List[str] = []

    form = await request.form()
    form_data = dict(form)
    allowed_envs = [str(x) for x in form.getlist("allowed_environments")]

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
        _ctx(request, title="Rule Diff Preview", errors=errors, diff_text=diff_text),
    )


@router.post("/rules/save")
async def rule_save(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)
    baseline_errors = validators.validate_bundle(bundle, paths.repo_root)

    form = await request.form()
    form_data = dict(form)
    allowed_envs = [str(x) for x in form.getlist("allowed_environments")]

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
            _ctx(request, title="Rule Save", errors=[str(exc)], diff_text="No changes."),
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
            _ctx(request, title="Rule Save", errors=messages, diff_text=diff_text),
        )

    try:
        config_store.save_bundle(paths, candidate, ["rules"])
    except Exception as exc:  # noqa: BLE001
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(
                request,
                title="Rule Save",
                errors=[f"Failed to write vm-configs/vm-env-rules.yaml: {exc}"],
                diff_text="No changes were persisted.",
            ),
        )

    return HTMLResponse("<div class='flash success'>Env rules saved.</div>", headers={"HX-Refresh": "true"})
