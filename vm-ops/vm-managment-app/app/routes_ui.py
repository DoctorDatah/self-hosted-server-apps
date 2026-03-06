#!/usr/bin/env python3
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from . import config_store, git_ops, validators

BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
router = APIRouter()


def _paths() -> config_store.ConfigPaths:
    return config_store.get_paths()


def _ctx(request: Request, **extra: Any) -> Dict[str, Any]:
    return {"request": request, **extra}


def _bool_from_form(form: Dict[str, Any], key: str, default: bool = False) -> bool:
    value = form.get(key)
    if value is None:
        return default
    return str(value).strip().lower() in {"1", "true", "on", "yes", "y"}


def _split_csv(raw: str) -> List[str]:
    return config_store.split_csv_values(raw)


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


@router.get("/")
def dashboard(request: Request):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    status = git_ops.get_status(paths.repo_root)
    validation_errors = validators.validate_bundle(bundle, paths.repo_root)

    machines = bundle.machines_doc.get("machines", {})
    operations = bundle.operations_doc.get("operations", {})
    rules = bundle.rules_doc.get("rules", {})

    return templates.TemplateResponse(
        "dashboard.html",
        _ctx(
            request,
            page_title="Dashboard",
            machines_count=len(machines),
            operations_count=len(operations),
            rules_count=len(rules),
            git_status=status,
            validation_errors=validation_errors,
        ),
    )


@router.get("/machines")
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
            status_code=400,
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        new_text = config_store.dump_doc(candidate.machines_doc)
        diff_text = config_store.render_diff(bundle.machines_text, new_text, "vm-configs/vm-machines.yaml")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Machine Save", errors=errors, diff_text=diff_text),
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["machines"])
    return HTMLResponse("<div class='flash success'>Machine config saved.</div>", headers={"HX-Refresh": "true"})


@router.post("/machines/delete")
async def machine_delete(request: Request, machine_id: str = Form(...)):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)

    config_store.delete_machine(candidate, machine_id)
    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        return HTMLResponse(
            "<div class='flash error'>Cannot delete machine: " + " | ".join(errors) + "</div>",
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["machines"])
    return HTMLResponse("<div class='flash success'>Machine deleted.</div>", headers={"HX-Refresh": "true"})


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
            status_code=400,
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        new_text = config_store.dump_doc(candidate.operations_doc)
        diff_text = config_store.render_diff(bundle.operations_text, new_text, "vm-configs/vm-operations.yaml")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Operation Save", errors=errors, diff_text=diff_text),
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["operations"])
    return HTMLResponse("<div class='flash success'>Operation config saved.</div>", headers={"HX-Refresh": "true"})


@router.post("/operations/delete")
async def operation_delete(request: Request, operation_id: str = Form(...)):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)

    config_store.delete_operation(candidate, operation_id)
    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        return HTMLResponse(
            "<div class='flash error'>Cannot delete operation: " + " | ".join(errors) + "</div>",
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["operations"])
    return HTMLResponse("<div class='flash success'>Operation deleted.</div>", headers={"HX-Refresh": "true"})


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
            status_code=400,
        )

    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        new_text = config_store.dump_doc(candidate.rules_doc)
        diff_text = config_store.render_diff(bundle.rules_text, new_text, "vm-configs/vm-env-rules.yaml")
        return templates.TemplateResponse(
            "partials/preview.html",
            _ctx(request, title="Rule Save", errors=errors, diff_text=diff_text),
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["rules"])
    return HTMLResponse("<div class='flash success'>Env rules saved.</div>", headers={"HX-Refresh": "true"})


@router.post("/rules/delete")
async def rule_delete(request: Request, setup_id: str = Form(...)):
    paths = _paths()
    bundle = config_store.load_bundle(paths)
    candidate = config_store.clone_bundle(bundle)

    config_store.delete_rule(candidate, setup_id)
    errors = validators.validate_bundle(candidate, paths.repo_root)
    if errors:
        return HTMLResponse(
            "<div class='flash error'>Cannot delete rule: " + " | ".join(errors) + "</div>",
            status_code=400,
        )

    config_store.save_bundle(paths, candidate, ["rules"])
    return HTMLResponse("<div class='flash success'>Rule deleted.</div>", headers={"HX-Refresh": "true"})
