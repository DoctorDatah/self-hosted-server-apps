#!/usr/bin/env python3
import asyncio
import json
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from ...core.realtime_bus import bus
from ...shared.responses import err, ok
from ...shared.schemas import (
    DeleteApplyRequest,
    DeletePreviewRequest,
    model_to_dict,
)
from .services import backups, config_store, git_ops, validators
from .services.cascade import preview_cascade
from .services.integrity import IntegrityError, build_delete_impact_report, summarize_dependents

router = APIRouter(tags=["config-management-api"])


def _diffs_for_changed_parts(
    bundle: config_store.ConfigBundle,
    candidate: config_store.ConfigBundle,
    changed_parts,
) -> Dict[str, str]:
    diffs: Dict[str, str] = {}
    if "machines" in changed_parts:
        diffs["vm-configs/vm-machines.yaml"] = config_store.render_diff(
            bundle.machines_text,
            config_store.dump_doc(candidate.machines_doc),
            "vm-configs/vm-machines.yaml",
        )
    if "operations" in changed_parts:
        diffs["vm-configs/vm-operations.yaml"] = config_store.render_diff(
            bundle.operations_text,
            config_store.dump_doc(candidate.operations_doc),
            "vm-configs/vm-operations.yaml",
        )
    if "rules" in changed_parts:
        diffs["vm-configs/vm-env-rules.yaml"] = config_store.render_diff(
            bundle.rules_text,
            config_store.dump_doc(candidate.rules_doc),
            "vm-configs/vm-env-rules.yaml",
        )
    return diffs


def _changed_files(parts) -> list[str]:
    mapping = {
        "machines": "vm-configs/vm-machines.yaml",
        "operations": "vm-configs/vm-operations.yaml",
        "rules": "vm-configs/vm-env-rules.yaml",
    }
    return [mapping[p] for p in parts if p in mapping]


@router.get("/api/status")
def status() -> Dict[str, Any]:
    paths = config_store.get_paths()
    bundle = config_store.load_bundle(paths)
    git_status = git_ops.get_status(paths.repo_root)
    validation_errors = validators.validate_bundle(bundle, paths.repo_root)
    backup_status = backups.get_backup_status(paths)
    return {
        **git_status,
        "validation_errors": validation_errors,
        "backup_status": backup_status,
    }


@router.post("/api/git/prepare-commit")
async def prepare_commit(request: Request) -> Dict[str, Any]:
    paths = config_store.get_paths()

    branch_name = ""
    commit_message = ""

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        payload = await request.json()
        branch_name = str(payload.get("branch_name", ""))
        commit_message = str(payload.get("commit_message", ""))
    else:
        form = await request.form()
        branch_name = str(form.get("branch_name", ""))
        commit_message = str(form.get("commit_message", ""))

    tracked_files = [
        "vm-configs/vm-machines.yaml",
        "vm-configs/vm-operations.yaml",
        "vm-configs/vm-env-rules.yaml",
    ]

    try:
        result = git_ops.prepare_commit(
            paths.repo_root,
            tracked_files=tracked_files,
            branch_name=branch_name or None,
            commit_message=commit_message or None,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return result


@router.get("/api/config/integrity/dependencies")
def dependencies(entity_type: str, entity_id: str) -> Dict[str, Any]:
    paths = config_store.get_paths()
    bundle = config_store.load_bundle(paths)

    try:
        report = build_delete_impact_report(bundle, paths.repo_root, entity_type=entity_type, entity_id=entity_id)
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=err(str(exc), code=exc.code)) from exc

    return ok(
        {
            "report": model_to_dict(report),
            "dependents_by_type": summarize_dependents(report),
        }
    )


@router.post("/api/config/integrity/delete-preview")
async def delete_preview(request: Request) -> Dict[str, Any]:
    paths = config_store.get_paths()
    bundle = config_store.load_bundle(paths)
    try:
        payload = DeletePreviewRequest(**(await request.json()))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=err(f"Invalid preview payload: {exc}", code="bad_payload")) from exc

    try:
        candidate, changed_parts, _validation_errors, report = preview_cascade(
            bundle,
            paths.repo_root,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            cascade=payload.cascade,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=err(str(exc), code=exc.code)) from exc

    would_block = bool(report.blockers) and not payload.cascade
    diffs = _diffs_for_changed_parts(bundle, candidate, changed_parts)

    return ok(
        {
            "would_block": would_block,
            "report": model_to_dict(report),
            "changed_parts": changed_parts,
            "changed_files": _changed_files(changed_parts),
            "diffs": diffs,
            "cascade_requested": payload.cascade,
        }
    )


@router.post("/api/config/integrity/delete-apply")
async def delete_apply(request: Request) -> Dict[str, Any]:
    paths = config_store.get_paths()
    bundle = config_store.load_bundle(paths)
    try:
        payload = DeleteApplyRequest(**(await request.json()))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=err(f"Invalid apply payload: {exc}", code="bad_payload")) from exc

    if not payload.confirm:
        raise HTTPException(status_code=400, detail=err("Deletion must be explicitly confirmed.", code="not_confirmed"))

    try:
        candidate, changed_parts, _validation_errors, report = preview_cascade(
            bundle,
            paths.repo_root,
            entity_type=payload.entity_type,
            entity_id=payload.entity_id,
            cascade=payload.cascade,
        )
    except IntegrityError as exc:
        raise HTTPException(status_code=400, detail=err(str(exc), code=exc.code)) from exc

    if not changed_parts:
        raise HTTPException(
            status_code=400,
            detail=err("No changes generated. Use delete-preview first.", code="no_changes"),
        )

    config_store.save_bundle(paths, candidate, changed_parts)
    files = _changed_files(changed_parts)
    published = bus.publish("config_changed", {"files": files, "source": "delete_apply"})

    return ok(
        {
            "saved": True,
            "changed_parts": changed_parts,
            "changed_files": files,
            "realtime_version": published.version,
            "report": model_to_dict(report),
        }
    )


@router.get("/api/realtime/config-events")
async def realtime_config_events(request: Request) -> StreamingResponse:
    async def stream():
        last_version = -1
        while True:
            if await request.is_disconnected():
                break

            snapshot = bus.snapshot()
            if snapshot.version != last_version:
                last_version = snapshot.version
                payload = {
                    "event": snapshot.event,
                    "version": snapshot.version,
                    "timestamp": snapshot.timestamp,
                    "data": snapshot.data,
                }
                yield f"event: {snapshot.event}\n"
                yield f"data: {json.dumps(payload)}\n\n"

            await asyncio.sleep(1.0)

    headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
    }
    return StreamingResponse(stream(), media_type="text/event-stream", headers=headers)
