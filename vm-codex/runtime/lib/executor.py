from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List
import subprocess

from .state import append_log, now, save_run


def execute_plan(root: Path, run: Dict[str, Any], dry_run: bool = False) -> Dict[str, Any]:
    run["state"] = "running"
    run["started_at"] = now()
    save_run(root, run)

    failures = 0
    for stage in run["stage_plans"]:
        if run.get("cancellation_requested"):
            run["state"] = "canceled"
            run["finished_at"] = now()
            save_run(root, run)
            return run

        stage_result = {
            "stage": stage["stage"],
            "status": "succeeded",
            "commands": [],
        }

        for cmd in stage["commands"]:
            stage_result["commands"].append(cmd)
            append_log(root, run["run_id"], f"[{stage['stage']}] $ {cmd}")
            if dry_run:
                continue

            completed = subprocess.run(
                cmd,
                shell=True,
                cwd=str(root),
                capture_output=True,
                text=True,
            )
            if completed.stdout:
                append_log(root, run["run_id"], completed.stdout.rstrip("\n"))
            if completed.stderr:
                append_log(root, run["run_id"], completed.stderr.rstrip("\n"))

            if completed.returncode != 0:
                stage_result["status"] = "failed"
                stage_result["error_class"] = "non_retryable_stage_error"
                stage_result["error_message"] = f"Command failed with exit code {completed.returncode}"
                failures += 1
                break

        run.setdefault("stage_results", []).append(stage_result)

        if stage_result["status"] != "succeeded":
            # Single target run: fail-fast after first failed stage.
            break

        run.setdefault("completed_stages", []).append(stage["stage"])
        save_run(root, run)

    run["finished_at"] = now()
    run["state"] = "failed" if failures else "succeeded"
    if failures:
        run["error_class"] = "non_retryable_stage_error"
    save_run(root, run)
    return run
