#!/usr/bin/env python3
import datetime as dt
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo


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


def default_branch_name(tz_name: str = "UTC") -> str:
    stamp = dt.datetime.now(ZoneInfo(tz_name)).strftime("%Y%m%d-%H%M%S")
    return f"config_update/update-{stamp}"


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


def current_branch(repo_root: Path) -> str:
    return _run_git(repo_root, ["rev-parse", "--abbrev-ref", "HEAD"]).stdout.strip()


def _branch_exists_local(repo_root: Path, branch_name: str) -> bool:
    return _run_git(repo_root, ["show-ref", "--verify", f"refs/heads/{branch_name}"], check=False).returncode == 0


def _branch_exists_remote(repo_root: Path, branch_name: str, remote_name: str = "origin") -> bool:
    return _run_git(
        repo_root,
        ["show-ref", "--verify", f"refs/remotes/{remote_name}/{branch_name}"],
        check=False,
    ).returncode == 0


def _ensure_branch_reference(repo_root: Path, branch_name: str, remote_name: str = "origin") -> None:
    if _branch_exists_local(repo_root, branch_name):
        return
    if _branch_exists_remote(repo_root, branch_name, remote_name=remote_name):
        _run_git(repo_root, ["branch", "--track", branch_name, f"{remote_name}/{branch_name}"])
        return
    _run_git(repo_root, ["branch", branch_name, "HEAD"])


def _related_branches(repo_root: Path, prefix: str = "config_update/update-", remote_name: str = "origin") -> List[str]:
    refs = _run_git(
        repo_root,
        [
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)",
            "refs/heads",
            f"refs/remotes/{remote_name}",
        ],
        check=False,
    ).stdout.splitlines()

    ordered: List[str] = []
    seen = set()
    for raw in refs:
        name = raw.strip()
        if not name:
            continue
        if name.startswith(f"{remote_name}/"):
            name = name[len(remote_name) + 1 :]
        if not name.startswith(prefix):
            continue
        if name in seen:
            continue
        seen.add(name)
        ordered.append(name)
    return ordered


def resolve_target_branch(
    repo_root: Path,
    explicit_branch: Optional[str] = None,
    preferred_branch: Optional[str] = None,
    fallback_tz: str = "UTC",
) -> Tuple[str, bool]:
    requested = (explicit_branch or "").strip()
    preferred = (preferred_branch or "").strip()

    if requested:
        exists = _branch_exists_local(repo_root, requested) or _branch_exists_remote(repo_root, requested)
        return requested, exists
    if preferred:
        exists = _branch_exists_local(repo_root, preferred) or _branch_exists_remote(repo_root, preferred)
        if exists:
            return preferred, True

    related = _related_branches(repo_root)
    if related:
        return related[0], True

    return default_branch_name(fallback_tz), False


def switch_branch(repo_root: Path, branch_name: str) -> Dict[str, str]:
    branch = (branch_name or "").strip()
    if not branch:
        raise GitOpsError("branch_name is required")
    _ensure_branch_reference(repo_root, branch)
    return {"branch": branch}


def push_branch(
    repo_root: Path,
    branch_name: Optional[str] = None,
    remote_name: str = "origin",
    set_upstream: bool = True,
) -> Dict[str, str]:
    remote = (remote_name or "").strip() or "origin"
    branch = (branch_name or "").strip() or current_branch(repo_root)
    if not branch:
        raise GitOpsError("Could not determine branch to push.")

    args = ["push"]
    if set_upstream:
        args.extend(["-u", remote, branch])
    else:
        args.extend([remote, branch])
    _run_git(repo_root, args)
    return {"remote": remote, "branch": branch}


def _copy_path(src: Path, dest: Path) -> None:
    if src.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        return
    if src.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)


def _prepare_worktree(
    repo_root: Path,
    branch: str,
    remote_name: str = "origin",
) -> Tuple[Path, str]:
    wt_root = repo_root / "vm-managment-app" / "app-data" / "git-worktrees"
    wt_root.mkdir(parents=True, exist_ok=True)
    wt_path = Path(
        tempfile.mkdtemp(
            prefix="config-branch-",
            dir=str(wt_root),
        )
    )

    local_exists = _branch_exists_local(repo_root, branch)
    remote_exists = _branch_exists_remote(repo_root, branch, remote_name=remote_name)
    if local_exists:
        start_ref = branch
    elif remote_exists:
        start_ref = f"{remote_name}/{branch}"
    else:
        start_ref = "HEAD"

    _run_git(repo_root, ["worktree", "add", "--detach", str(wt_path), start_ref])
    return wt_path, start_ref


def prepare_commit(
    repo_root: Path,
    tracked_files: List[str],
    branch_name: Optional[str] = None,
    preferred_branch: Optional[str] = None,
    fallback_tz: str = "UTC",
    commit_message: Optional[str] = None,
) -> Dict[str, object]:
    branch, _branch_exists = resolve_target_branch(
        repo_root,
        explicit_branch=branch_name,
        preferred_branch=preferred_branch,
        fallback_tz=fallback_tz,
    )
    message = (commit_message or "").strip() or default_commit_message()

    wt_path: Optional[Path] = None
    try:
        wt_path, _ = _prepare_worktree(repo_root, branch)

        existing_paths: List[str] = []
        for rel in tracked_files:
            src = repo_root / rel
            dest = wt_path / rel
            if src.exists():
                _copy_path(src, dest)
                existing_paths.append(rel)

        if not existing_paths:
            raise GitOpsError("No tracked config files found to stage.")

        _run_git(wt_path, ["add", "--", *existing_paths])
        staged = _run_git(wt_path, ["diff", "--cached", "--name-only"]).stdout.splitlines()
        staged_files = [x.strip() for x in staged if x.strip()]
        if not staged_files:
            raise GitOpsError("No staged changes in tracked config files.")

        _run_git(wt_path, ["commit", "-m", message])
        commit_sha = _run_git(wt_path, ["rev-parse", "HEAD"]).stdout.strip()
        short_sha = _run_git(wt_path, ["rev-parse", "--short", "HEAD"]).stdout.strip()
        _run_git(repo_root, ["branch", "-f", branch, commit_sha])
    finally:
        if wt_path is not None:
            _run_git(repo_root, ["worktree", "remove", "--force", str(wt_path)], check=False)
            if wt_path.exists():
                shutil.rmtree(wt_path, ignore_errors=True)

    return {
        "branch": branch,
        "commit_sha": short_sha,
        "changed_files": staged_files,
        "next_commands": [
            f"git push -u origin {branch}",
            "gh pr create --fill",
        ],
    }
