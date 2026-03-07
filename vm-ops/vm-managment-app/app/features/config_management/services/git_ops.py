#!/usr/bin/env python3
import datetime as dt
import json
import os
import pty
import re
import select
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote
from zoneinfo import ZoneInfo


class GitOpsError(Exception):
    pass


CONFIG_BRANCH_PREFIX = "config_update/"
DEVICE_CODE_PATTERN = re.compile(r"\b[A-Z0-9]{4}-[A-Z0-9]{4}\b")
SENSITIVE_LOCAL_PATH_PREFIXES = (
    "vm-managment-app/app-data/",
)


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


def list_tracked_sensitive_files(repo_root: Path) -> List[str]:
    proc = _run_git(repo_root, ["ls-files"], check=False)
    tracked = [str(x).strip() for x in (proc.stdout or "").splitlines() if str(x).strip()]
    return [
        path
        for path in tracked
        if any(path.startswith(prefix) for prefix in SENSITIVE_LOCAL_PATH_PREFIXES)
    ]


def assert_no_tracked_sensitive_files(repo_root: Path) -> None:
    tracked_sensitive = list_tracked_sensitive_files(repo_root)
    if tracked_sensitive:
        joined = ", ".join(tracked_sensitive[:5])
        extra = "" if len(tracked_sensitive) <= 5 else f" (+{len(tracked_sensitive) - 5} more)"
        raise GitOpsError(
            "Sensitive local app data is tracked by git. "
            "Remove it from git index and keep it ignored. "
            f"Tracked paths: {joined}{extra}"
        )


def _resolve_gh_exec() -> str:
    gh_bin = (os.environ.get("GH_BIN", "") or "").strip()
    candidates = [gh_bin] if gh_bin else []
    if not candidates:
        resolved = shutil.which("gh")
        if resolved:
            candidates.append(resolved)
    candidates.extend(
        [
            "/opt/homebrew/bin/gh",
            "/usr/local/bin/gh",
            "/usr/bin/gh",
        ]
    )
    gh_exec = ""
    for candidate in candidates:
        value = (candidate or "").strip()
        if value and Path(value).exists():
            gh_exec = value
            break

    return gh_exec


def _gh_env(repo_root: Path) -> Dict[str, str]:
    env = os.environ.copy()
    gh_cfg_dir = repo_root / "vm-managment-app" / "app-data" / "gh-config"
    gh_cfg_dir.mkdir(parents=True, exist_ok=True)
    env["GH_CONFIG_DIR"] = str(gh_cfg_dir)
    return env


def github_connection_status(repo_root: Path) -> Dict[str, Any]:
    gh_exec = _resolve_gh_exec()
    if not gh_exec:
        return {
            "available": False,
            "authenticated": False,
            "gh_path": "",
            "username": "",
            "message": "GitHub CLI not found. Install `gh` and run `gh auth login --web`.",
        }

    proc = subprocess.run(
        [gh_exec, "auth", "status", "--hostname", "github.com"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        check=False,
        env=_gh_env(repo_root),
    )
    combined = "\n".join([proc.stdout or "", proc.stderr or ""]).strip()
    authenticated = proc.returncode == 0
    username = ""
    match = re.search(r"Logged in to github\.com as ([A-Za-z0-9-]+)", combined)
    if not match:
        match = re.search(r"github\.com account ([A-Za-z0-9-]+)", combined)
    if match:
        username = match.group(1)

    if not authenticated:
        token_proc = subprocess.run(
            [gh_exec, "auth", "token", "--hostname", "github.com"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            env=_gh_env(repo_root),
        )
        token_text = (token_proc.stdout or "").strip()
        if token_proc.returncode == 0 and token_text:
            authenticated = True

    if authenticated and not username:
        user_proc = subprocess.run(
            [gh_exec, "api", "user", "--jq", ".login"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=8,
            env=_gh_env(repo_root),
        )
        user_text = (user_proc.stdout or "").strip()
        if user_proc.returncode == 0 and user_text:
            username = user_text

    if authenticated:
        msg = f"Connected as {username}." if username else "Connected to github.com."
    else:
        msg = "Not authenticated. Run `gh auth login --web`."

    return {
        "available": True,
        "authenticated": authenticated,
        "gh_path": gh_exec,
        "username": username,
        "message": msg,
    }


def _run_gh(
    repo_root: Path,
    args: List[str],
    check: bool = True,
    input_text: Optional[str] = None,
    timeout_sec: Optional[int] = None,
) -> subprocess.CompletedProcess:
    gh_exec = _resolve_gh_exec()
    if not gh_exec:
        raise GitOpsError(
            "GitHub CLI 'gh' is not installed or not in PATH. "
            "Install it and ensure shell PATH includes it, or set GH_BIN=/absolute/path/to/gh."
        )

    try:
        proc = subprocess.run(
            [gh_exec, *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            input=input_text,
            timeout=timeout_sec,
            env=_gh_env(repo_root),
        )
    except subprocess.TimeoutExpired as exc:
        raise GitOpsError(f"gh {' '.join(args)} timed out.") from exc
    except FileNotFoundError as exc:
        raise GitOpsError(
            "GitHub CLI 'gh' is not installed or not in PATH. "
            "Install it and ensure shell PATH includes it, or set GH_BIN=/absolute/path/to/gh."
        ) from exc
    if check and proc.returncode != 0:
        raise GitOpsError(proc.stderr.strip() or proc.stdout.strip() or f"gh {' '.join(args)} failed")
    return proc


def _read_device_code_from_clipboard() -> str:
    commands = [
        ["pbpaste"],  # macOS
        ["xclip", "-o", "-selection", "clipboard"],  # Linux X11
        ["wl-paste", "-n"],  # Linux Wayland
    ]
    for cmd in commands:
        if shutil.which(cmd[0]) is None:
            continue
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=2)
        except Exception:
            continue
        text = (proc.stdout or "").strip()
        match = DEVICE_CODE_PATTERN.search(text)
        if match:
            return match.group(0)
    return ""


def _extract_device_code(text: str) -> str:
    match = DEVICE_CODE_PATTERN.search(str(text or ""))
    return match.group(0) if match else ""


def _poll_clipboard_for_device_code(max_wait_seconds: float = 12.0, interval_seconds: float = 0.5) -> str:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        code = _read_device_code_from_clipboard()
        if code:
            return code
        time.sleep(interval_seconds)
    return ""


def read_device_code_hint() -> str:
    return _read_device_code_from_clipboard()


def _connect_github_web_with_pipe(repo_root: Path, args: List[str]) -> Tuple[subprocess.Popen, str, bool]:
    proc = subprocess.Popen(  # noqa: S603
        args,
        cwd=str(repo_root),
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        if proc.stdin:
            proc.stdin.write("\n")
            proc.stdin.flush()
            proc.stdin.close()
    except Exception:
        pass

    combined = ""
    finished = False
    try:
        out, err = proc.communicate(timeout=8)
        combined = "\n".join([out or "", err or ""]).strip()
        finished = True
    except subprocess.TimeoutExpired as timeout_exc:
        partial_out = timeout_exc.output or ""
        partial_err = timeout_exc.stderr or ""
        combined = "\n".join([partial_out, partial_err]).strip()
        finished = False
    return proc, combined, finished


def _connect_github_web_with_pty(repo_root: Path, args: List[str]) -> Tuple[subprocess.Popen, str, bool]:
    master_fd, slave_fd = pty.openpty()
    proc: Optional[subprocess.Popen] = None
    combined_parts: List[str] = []
    finished = False
    try:
        proc = subprocess.Popen(  # noqa: S603
            args,
            cwd=str(repo_root),
            stdin=slave_fd,
            stdout=slave_fd,
            stderr=slave_fd,
            text=False,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        try:
            os.close(slave_fd)
        except OSError:
            pass

    if proc is None:
        raise GitOpsError("Failed to start GitHub browser OAuth process.")

    try:
        try:
            os.write(master_fd, b"\n")
        except OSError:
            pass

        deadline = time.time() + 16.0
        while time.time() < deadline:
            rc = proc.poll()
            if rc is not None:
                finished = True

            ready, _, _ = select.select([master_fd], [], [], 0.35)
            if ready:
                try:
                    chunk = os.read(master_fd, 4096)
                except OSError:
                    break
                if not chunk:
                    if finished:
                        break
                    continue
                combined_parts.append(chunk.decode("utf-8", errors="replace"))
                if _extract_device_code("".join(combined_parts)):
                    break
            elif finished:
                break
    finally:
        try:
            os.close(master_fd)
        except OSError:
            pass

    combined = "".join(combined_parts).strip()
    return proc, combined, finished


def connect_github_web(
    repo_root: Path,
    git_protocol: str = "https",
    hostname: str = "github.com",
) -> Dict[str, Any]:
    proto = (git_protocol or "").strip() or "https"
    host = (hostname or "").strip() or "github.com"
    gh_exec = _resolve_gh_exec()
    if not gh_exec:
        raise GitOpsError(
            "GitHub CLI 'gh' is not installed or not in PATH. "
            "Install it and ensure shell PATH includes it, or set GH_BIN=/absolute/path/to/gh."
        )
    args = [
        gh_exec,
        "auth",
        "login",
        "--web",
        "--clipboard",
        "--hostname",
        host,
        "--git-protocol",
        proto,
        "--skip-ssh-key",
    ]

    try:
        # Non-blocking launch: return immediately so UI/server does not hang.
        proc = subprocess.Popen(  # noqa: S603
            args,
            cwd=str(repo_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            start_new_session=True,
            close_fds=True,
            env=_gh_env(repo_root),
        )
        # Accept default prompts without blocking the request lifecycle.
        try:
            if proc.stdin:
                proc.stdin.write("\n")
                proc.stdin.flush()
                proc.stdin.close()
        except Exception:
            pass
    except Exception as exc:  # noqa: BLE001
        raise GitOpsError(f"Failed to launch GitHub browser OAuth: {exc}") from exc

    # Best effort only; primary path is UI clipboard read.
    device_code = _poll_clipboard_for_device_code(max_wait_seconds=1.5, interval_seconds=0.25)
    message = "GitHub browser OAuth launched. Use 'Show Device Code' to read the code from clipboard."

    return {
        "ok": True,
        "pid": proc.pid,
        "device_code": device_code,
        "auth_url": f"https://{host}/login/device",
        "message": message,
    }


def disconnect_github(
    repo_root: Path,
    hostname: str = "github.com",
) -> Dict[str, Any]:
    host = (hostname or "").strip() or "github.com"
    status = github_connection_status(repo_root)
    user = str(status.get("username", "") or "").strip()

    args = ["auth", "logout", "--hostname", host]
    if user:
        args.extend(["--user", user])
    proc = _run_gh(
        repo_root,
        args,
        check=False,
        input_text="y\n",
        timeout_sec=60,
    )
    combined = "\n".join([proc.stdout or "", proc.stderr or ""]).strip()
    if proc.returncode != 0:
        raise GitOpsError(combined or "GitHub disconnect failed.")
    return {
        "ok": True,
        "message": combined or "GitHub disconnected.",
    }


def default_branch_name(tz_name: str = "UTC") -> str:
    # Git branch names cannot include ":" so time separator uses "-".
    stamp = dt.datetime.now(ZoneInfo(tz_name)).strftime("%B-%d-%Y--%I-%M-%p")
    return f"{CONFIG_BRANCH_PREFIX}{stamp}"


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


def _remote_url(repo_root: Path, remote_name: str = "origin") -> str:
    proc = _run_git(repo_root, ["config", "--get", f"remote.{remote_name}.url"], check=False)
    return (proc.stdout or "").strip()


def _github_repo_web_url_from_remote(remote_url: str) -> str:
    raw = (remote_url or "").strip()
    if not raw:
        return ""

    path = ""
    if raw.startswith("git@github.com:"):
        path = raw.split("git@github.com:", 1)[1]
    elif raw.startswith("ssh://git@github.com/"):
        path = raw.split("ssh://git@github.com/", 1)[1]
    elif raw.startswith("https://github.com/"):
        path = raw.split("https://github.com/", 1)[1]
    elif raw.startswith("http://github.com/"):
        path = raw.split("http://github.com/", 1)[1]
    else:
        return ""

    if path.endswith(".git"):
        path = path[:-4]
    path = path.strip("/")
    if not path or "/" not in path:
        return ""
    return f"https://github.com/{path}"


def github_repo_web_url(repo_root: Path, remote_name: str = "origin") -> str:
    return _github_repo_web_url_from_remote(_remote_url(repo_root, remote_name=remote_name))


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


def _related_branches(repo_root: Path, prefix: str = CONFIG_BRANCH_PREFIX, remote_name: str = "origin") -> List[str]:
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
        if not _is_related_pr(requested):
            raise GitOpsError(f"branch_name must start with '{CONFIG_BRANCH_PREFIX}' for config management.")
        exists = _branch_exists_local(repo_root, requested) or _branch_exists_remote(repo_root, requested)
        return requested, exists
    if preferred:
        if _is_related_pr(preferred):
            exists = _branch_exists_local(repo_root, preferred) or _branch_exists_remote(repo_root, preferred)
            if exists:
                return preferred, True

    # Prefer an active related/open PR branch when available.
    try:
        open_prs = list_open_prs(
            repo_root,
            preferred_branch=preferred,
            related_only=True,
            limit=100,
        )
        for pr in open_prs:
            head = str(pr.get("head", "") or "").strip()
            if not head:
                continue
            exists = _branch_exists_local(repo_root, head) or _branch_exists_remote(repo_root, head)
            return head, exists
    except Exception:
        pass

    related = _related_branches(repo_root)
    if related:
        return related[0], True

    return default_branch_name(fallback_tz), False


def switch_branch(repo_root: Path, branch_name: str) -> Dict[str, str]:
    branch = (branch_name or "").strip()
    if not branch:
        raise GitOpsError("branch_name is required")
    if not _is_related_pr(branch):
        raise GitOpsError(f"branch_name must start with '{CONFIG_BRANCH_PREFIX}' for config management.")
    _ensure_branch_reference(repo_root, branch)
    return {"branch": branch}


def push_branch(
    repo_root: Path,
    branch_name: Optional[str] = None,
    remote_name: str = "origin",
    set_upstream: bool = True,
) -> Dict[str, str]:
    remote = (remote_name or "").strip() or "origin"
    branch = (branch_name or "").strip()
    if not branch:
        raise GitOpsError("branch_name is required for push (no fallback to local current branch).")
    if not _is_related_pr(branch):
        raise GitOpsError(f"branch_name must start with '{CONFIG_BRANCH_PREFIX}' for config management.")

    args = ["push"]
    if set_upstream:
        args.extend(["-u", remote, branch])
    else:
        args.extend([remote, branch])
    _run_git(repo_root, args)
    return {"remote": remote, "branch": branch}


def _is_related_pr(head_branch: str, preferred_branch: str = "") -> bool:
    head = (head_branch or "").strip()
    preferred = (preferred_branch or "").strip()
    if not head:
        return False
    if preferred and head == preferred:
        return True
    return head.startswith(CONFIG_BRANCH_PREFIX)


def is_related_config_branch(branch_name: str, preferred_branch: str = "") -> bool:
    return _is_related_pr(branch_name, preferred_branch=preferred_branch)


def list_open_prs(
    repo_root: Path,
    preferred_branch: str = "",
    related_only: bool = True,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    proc = _run_gh(
        repo_root,
        [
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            str(max(1, int(limit))),
            "--json",
            "number,title,headRefName,baseRefName,url,updatedAt,author",
        ],
    )

    try:
        rows = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise GitOpsError(f"Failed to parse gh pr list output: {exc}") from exc
    if not isinstance(rows, list):
        raise GitOpsError("Unexpected gh pr list payload.")

    items: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        head = str(row.get("headRefName", "") or "")
        if related_only and not _is_related_pr(head, preferred_branch=preferred_branch):
            continue

        author = row.get("author", {})
        author_login = ""
        if isinstance(author, dict):
            author_login = str(author.get("login", "") or "")

        items.append(
            {
                "number": row.get("number"),
                "title": str(row.get("title", "") or ""),
                "head": head,
                "base": str(row.get("baseRefName", "") or ""),
                "url": str(row.get("url", "") or ""),
                "updated_at": str(row.get("updatedAt", "") or ""),
                "author": author_login,
            }
        )
    items.sort(key=lambda x: str(x.get("updated_at", "") or ""), reverse=True)
    return items


def list_related_branches(
    repo_root: Path,
    preferred_branch: str = "",
    limit: int = 100,
    remote_name: str = "origin",
) -> List[Dict[str, Any]]:
    repo_web_url = github_repo_web_url(repo_root, remote_name=remote_name)
    refs = _run_git(
        repo_root,
        [
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)|%(committerdate:iso8601)",
            "refs/heads",
            f"refs/remotes/{remote_name}",
        ],
        check=False,
    ).stdout.splitlines()

    index: Dict[str, Dict[str, Any]] = {}
    ordered: List[str] = []
    preferred = (preferred_branch or "").strip()
    max_items = max(1, int(limit))

    for raw in refs:
        line = raw.strip()
        if not line:
            continue
        parts = line.split("|", 1)
        ref_name = parts[0].strip()
        commit_at = parts[1].strip() if len(parts) > 1 else ""

        is_local = ref_name.startswith("refs/heads/") or not ref_name.startswith(f"{remote_name}/")
        branch_name = ref_name
        if branch_name.startswith(f"{remote_name}/"):
            branch_name = branch_name[len(remote_name) + 1 :]
            is_local = False

        if not _is_related_pr(branch_name, preferred_branch=preferred):
            continue

        if branch_name not in index:
            index[branch_name] = {
                "branch": branch_name,
                "local_exists": False,
                "remote_exists": False,
                "last_commit_at": commit_at,
                "is_preferred": bool(preferred and branch_name == preferred),
                "github_url": f"{repo_web_url}/tree/{quote(branch_name, safe='/')}" if repo_web_url else "",
            }
            ordered.append(branch_name)

        if is_local:
            index[branch_name]["local_exists"] = True
        else:
            index[branch_name]["remote_exists"] = True

        existing_commit = str(index[branch_name].get("last_commit_at", "") or "")
        if commit_at and (not existing_commit or commit_at > existing_commit):
            index[branch_name]["last_commit_at"] = commit_at

    return [index[name] for name in ordered[:max_items]]


def create_pr(
    repo_root: Path,
    head_branch: str,
    base_branch: str = "main",
    title: str = "",
    body: str = "",
    use_fill: bool = True,
) -> Dict[str, str]:
    head = (head_branch or "").strip()
    base = (base_branch or "").strip() or "main"
    pr_title = (title or "").strip()
    pr_body = body or ""

    if not head:
        raise GitOpsError("head branch is required to create PR.")
    if not _is_related_pr(head):
        raise GitOpsError(f"head branch must start with '{CONFIG_BRANCH_PREFIX}' for config management.")

    args: List[str] = ["pr", "create", "--base", base, "--head", head]
    if use_fill:
        args.append("--fill")
        if pr_title:
            args.extend(["--title", pr_title])
        if pr_body.strip():
            args.extend(["--body", pr_body])
    else:
        if not pr_title:
            raise GitOpsError("title is required when fill mode is disabled.")
        args.extend(["--title", pr_title, "--body", pr_body])

    proc = _run_gh(repo_root, args)
    out_lines = [x.strip() for x in (proc.stdout or "").splitlines() if x.strip()]
    pr_url = out_lines[-1] if out_lines else ""
    return {
        "url": pr_url,
        "head": head,
        "base": base,
    }


def close_pr(
    repo_root: Path,
    pr_number: int,
    delete_branch: bool = False,
) -> Dict[str, Any]:
    number = int(pr_number)
    if number <= 0:
        raise GitOpsError("pr_number must be a positive integer.")

    args = ["pr", "close", str(number)]
    if delete_branch:
        args.append("--delete-branch")
    proc = _run_gh(repo_root, args)
    output = (proc.stdout or "").strip()
    return {
        "number": number,
        "delete_branch": bool(delete_branch),
        "output": output,
    }


def delete_branch(
    repo_root: Path,
    branch_name: str,
    delete_local: bool = True,
    delete_remote: bool = True,
    remote_name: str = "origin",
) -> Dict[str, Any]:
    branch = (branch_name or "").strip()
    remote = (remote_name or "").strip() or "origin"
    if not branch:
        raise GitOpsError("branch_name is required.")
    if not _is_related_pr(branch):
        raise GitOpsError(f"branch_name must start with '{CONFIG_BRANCH_PREFIX}' for config management.")
    if not delete_local and not delete_remote:
        raise GitOpsError("Select local and/or remote branch delete.")
    if current_branch(repo_root) == branch:
        raise GitOpsError("Cannot delete the currently checked-out local branch.")

    local_deleted = False
    remote_deleted = False

    if delete_local and _branch_exists_local(repo_root, branch):
        _run_git(repo_root, ["branch", "-D", branch])
        local_deleted = True

    if delete_remote and _branch_exists_remote(repo_root, branch, remote_name=remote):
        _run_git(repo_root, ["push", remote, "--delete", branch])
        remote_deleted = True

    return {
        "branch": branch,
        "local_deleted": local_deleted,
        "remote_deleted": remote_deleted,
        "remote": remote,
    }


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
    assert_no_tracked_sensitive_files(repo_root)

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
