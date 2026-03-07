#!/usr/bin/env python3
import json
import os
import shlex
import subprocess
from pathlib import Path
from typing import Any, Dict

from ..lib.resolve import resolve_secret


def run_ssh_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    target: Dict[str, Any],
    stage_id: str,
    params: Dict[str, Any],
    merged_config: Dict[str, Any],
) -> subprocess.CompletedProcess:
    ssh = target.get("ssh", {})
    host = ssh.get("host")
    user = ssh.get("user")
    port = ssh.get("port", 22)
    key_ref = ssh.get("key_ref")
    repo_path = target.get("repo_path", "/opt/vm-codex-v2")

    if not host or not user:
        return subprocess.CompletedProcess(args=["ssh"], returncode=2, stdout="", stderr="Missing target.ssh.host or target.ssh.user")

    key_file = None
    if key_ref:
        secret = resolve_secret(repo_root, str(key_ref))
        key_file = run_dir / "ssh_key"
        key_file.write_text(secret + "\n", encoding="utf-8")
        key_file.chmod(0o600)

    env_exports = {
        "VMCX_STAGE_ID": stage_id,
        "VMCX_TARGET_ID": str(target.get("target_id", "")),
        "VMCX_EXEC_MODE": "ssh",
        "VMCX_PARAMS_JSON": json.dumps(params),
        "VMCX_MERGED_CONFIG_JSON": json.dumps(merged_config),
        "VMCX_RUN_DIR": str(run_dir),
        "VMCX_REPO_ROOT": str(repo_path),
    }

    export_cmd = " ".join(
        f"{k}={shlex.quote(v)}" for k, v in env_exports.items()
    )
    remote = f"cd {shlex.quote(str(repo_path))} && {export_cmd} bash vm-setups/{shlex.quote(stage_id)}/stage.sh"

    cmd = [
        "ssh",
        "-p",
        str(port),
        "-o",
        "BatchMode=yes",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if key_file:
        cmd.extend(["-i", str(key_file)])
    cmd.append(f"{user}@{host}")
    cmd.append(remote)

    return subprocess.run(
        cmd,
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
