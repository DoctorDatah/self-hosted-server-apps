#!/usr/bin/env python3
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from . import config_store, git_ops, validators

router = APIRouter(prefix="/api", tags=["api"])


@router.get("/status")
def status() -> Dict[str, Any]:
    paths = config_store.get_paths()
    bundle = config_store.load_bundle(paths)
    git_status = git_ops.get_status(paths.repo_root)
    validation_errors = validators.validate_bundle(bundle, paths.repo_root)
    return {
        **git_status,
        "validation_errors": validation_errors,
    }


@router.post("/git/prepare-commit")
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
