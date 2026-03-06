#!/usr/bin/env python3
import datetime as dt
import json
import os
import random
import string
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .io_utils import ensure_dir, load_data_file, write_json
from ..executors.local import run_local_stage
from ..executors.ssh import run_ssh_stage


class RunError(Exception):
    pass


def _timestamp() -> str:
    return dt.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_run_id() -> str:
    now = dt.datetime.utcnow().strftime("%Y-%m-%d-%H%M%S")
    suffix = "".join(random.choices(string.digits, k=3))
    return f"run-{now}-{suffix}"


def _runs_root(repo_root: Path) -> Path:
    return repo_root / "local-state" / "runs"


def create_run(plan: Dict[str, Any], repo_root: Path) -> Tuple[str, Path]:
    run_id = generate_run_id()
    run_dir = _runs_root(repo_root) / run_id
    ensure_dir(run_dir)

    write_json(run_dir / "plan.json", plan)
    status = {
        "run_id": run_id,
        "state": "pending",
        "created_at": _timestamp(),
        "updated_at": _timestamp(),
        "target_id": plan["target_id"],
        "exec_mode": plan["exec_mode"],
        "stages": plan["stages"],
        "completed_stages": [],
        "failed_stage": None,
        "error": None,
    }
    write_json(run_dir / "status.json", status)
    return run_id, run_dir


def load_status(repo_root: Path, run_id: str) -> Dict[str, Any]:
    status_path = _runs_root(repo_root) / run_id / "status.json"
    return load_data_file(status_path)


def _save_status(repo_root: Path, run_id: str, status: Dict[str, Any]) -> None:
    status["updated_at"] = _timestamp()
    write_json(_runs_root(repo_root) / run_id / "status.json", status)


def _stage_runner(plan: Dict[str, Any], stage_id: str, run_dir: Path, repo_root: Path) -> subprocess.CompletedProcess:
    target = plan["target"]
    if plan["exec_mode"] == "local":
        return run_local_stage(
            repo_root=repo_root,
            run_dir=run_dir,
            target=target,
            stage_id=stage_id,
            params=plan["resolved_params"],
            merged_config=plan["merged_config"],
        )

    return run_ssh_stage(
        repo_root=repo_root,
        run_dir=run_dir,
        target=target,
        stage_id=stage_id,
        params=plan["resolved_params"],
        merged_config=plan["merged_config"],
    )


def execute_run(plan: Dict[str, Any], repo_root: Path, confirm: bool, start_index: int = 0) -> str:
    if not confirm:
        raise RunError("Mutating run requires --confirm")

    run_id, run_dir = create_run(plan, repo_root)
    status = load_status(repo_root, run_id)
    status["state"] = "running"
    _save_status(repo_root, run_id, status)

    stages: List[str] = list(plan["stages"])
    for idx in range(start_index, len(stages)):
        stage_id = stages[idx]
        proc = _stage_runner(plan, stage_id, run_dir, repo_root)
        log_path = run_dir / f"{idx+1:02d}-{stage_id}.log"
        log_path.write_text(
            (proc.stdout or "") + "\n" + (proc.stderr or ""),
            encoding="utf-8",
        )

        if proc.returncode != 0:
            status = load_status(repo_root, run_id)
            status["state"] = "failed"
            status["failed_stage"] = stage_id
            status["error"] = f"stage {stage_id} failed with exit code {proc.returncode}"
            _save_status(repo_root, run_id, status)
            raise RunError(f"Run {run_id} failed at stage {stage_id}")

        status = load_status(repo_root, run_id)
        completed = list(status.get("completed_stages", []))
        completed.append(stage_id)
        status["completed_stages"] = completed
        _save_status(repo_root, run_id, status)

    status = load_status(repo_root, run_id)
    status["state"] = "succeeded"
    status["failed_stage"] = None
    status["error"] = None
    status["ended_at"] = _timestamp()
    _save_status(repo_root, run_id, status)
    return run_id


def resume_run(repo_root: Path, run_id: str, confirm: bool) -> str:
    if not confirm:
        raise RunError("Resume requires --confirm")

    run_dir = _runs_root(repo_root) / run_id
    plan = load_data_file(run_dir / "plan.json")
    status = load_status(repo_root, run_id)

    if status.get("state") == "succeeded":
        raise RunError(f"Run {run_id} already succeeded")

    failed_stage = status.get("failed_stage")
    stages = plan.get("stages", [])
    if failed_stage and failed_stage in stages:
        start_index = stages.index(failed_stage)
    else:
        completed = status.get("completed_stages", [])
        start_index = len(completed)

    # Resume creates a new run id for auditability while preserving source run context.
    plan["resumed_from_run_id"] = run_id
    return execute_run(plan=plan, repo_root=repo_root, confirm=confirm, start_index=start_index)


def cancel_run(repo_root: Path, run_id: str) -> Dict[str, Any]:
    status = load_status(repo_root, run_id)
    if status.get("state") in {"succeeded", "failed", "canceled"}:
        return status
    status["state"] = "canceled"
    _save_status(repo_root, run_id, status)
    return status
