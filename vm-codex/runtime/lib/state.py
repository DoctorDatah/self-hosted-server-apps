from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import json
import uuid


def ensure_dirs(root: Path) -> Dict[str, Path]:
    state_dir = root / "vm-codex" / "local-state"
    runs_dir = state_dir / "runs"
    logs_dir = state_dir / "logs"
    backups_dir = state_dir / "backups"
    for directory in (state_dir, runs_dir, logs_dir, backups_dir):
        directory.mkdir(parents=True, exist_ok=True)
    return {
        "state": state_dir,
        "runs": runs_dir,
        "logs": logs_dir,
        "backups": backups_dir,
    }


def new_run_id() -> str:
    return f"run-{uuid.uuid4()}"


def run_file(root: Path, run_id: str) -> Path:
    dirs = ensure_dirs(root)
    return dirs["runs"] / f"{run_id}.json"


def log_file(root: Path, run_id: str) -> Path:
    dirs = ensure_dirs(root)
    return dirs["logs"] / f"{run_id}.log"


def save_run(root: Path, run: Dict[str, Any]) -> None:
    path = run_file(root, run["run_id"])
    path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")


def load_run(root: Path, run_id: str) -> Dict[str, Any]:
    path = run_file(root, run_id)
    if not path.exists():
        raise FileNotFoundError(f"Unknown run_id: {run_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def append_log(root: Path, run_id: str, line: str) -> None:
    path = log_file(root, run_id)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line.rstrip("\n") + "\n")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()
