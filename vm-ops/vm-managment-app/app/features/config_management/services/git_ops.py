#!/usr/bin/env python3
import datetime as dt
import secrets
import subprocess
from pathlib import Path
from typing import Dict, List, Optional


class GitOpsError(Exception):
    pass


def _run_git(repo_root: Path, args: List[str], check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise GitOpsError(proc.stderr.strip() or proc.stdout.strip() or f"git {' '.join(args)} failed")
    return proc


def default_branch_name() -> str:
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    suffix = secrets.token_hex(2)
    return f"vm-managment-app/config-update-{stamp}-{suffix}"


def default_commit_message() -> str:
    return "chore(vm-configs): update config via vm-managment-app"


def get_status(repo_root: Path) -> Dict[str, object]:
    branch = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    changed = _run_git(repo_root, ["status", "--porcelain"], check=False).stdout.splitlines()
    staged = _run_git(repo_root, ["diff", "--cached", "--name-only"], check=False).stdout.splitlines()

    changed_files: List[str] = []
    for line in changed:
        if not line.strip():
            continue
        # porcelain format: XY <path>
        path = line[3:].strip() if len(line) > 3 else line.strip()
        changed_files.append(path)

    return {
        "branch": branch,
        "is_clean": len(changed_files) == 0,
        "changed_files": changed_files,
        "staged_files": [x.strip() for x in staged if x.strip()],
    }


def _ensure_branch(repo_root: Path, branch_name: str) -> None:
    current = _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()
    if current == branch_name:
        return

    exists = _run_git(repo_root, ["show-ref", "--verify", f"refs/heads/{branch_name}"], check=False)
    if exists.returncode == 0:
        _run_git(repo_root, ["checkout", branch_name])
    else:
        _run_git(repo_root, ["checkout", "-b", branch_name])


def prepare_commit(
    repo_root: Path,
    tracked_files: List[str],
    branch_name: Optional[str] = None,
    commit_message: Optional[str] = None,
) -> Dict[str, object]:
    branch = (branch_name or "").strip() or default_branch_name()
    message = (commit_message or "").strip() or default_commit_message()

    _ensure_branch(repo_root, branch)
    _run_git(repo_root, ["add", "--", *tracked_files])

    staged = _run_git(repo_root, ["diff", "--cached", "--name-only"]).stdout.splitlines()
    staged_files = [x.strip() for x in staged if x.strip()]
    if not staged_files:
        raise GitOpsError("No staged changes in tracked config files.")

    _run_git(repo_root, ["commit", "-m", message])
    sha = _run_git(repo_root, ["rev-parse", "--short", "HEAD"]).stdout.strip()

    return {
        "branch": branch,
        "commit_sha": sha,
        "changed_files": staged_files,
        "next_commands": [
            f"git push -u origin {branch}",
            "gh pr create --fill",
        ],
    }
