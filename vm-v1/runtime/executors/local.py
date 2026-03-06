#!/usr/bin/env python3
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Dict


def run_local_stage(
    *,
    repo_root: Path,
    run_dir: Path,
    target: Dict[str, Any],
    stage_id: str,
    params: Dict[str, Any],
    merged_config: Dict[str, Any],
) -> subprocess.CompletedProcess:
    stage_script = repo_root / "stages" / stage_id / "stage.sh"
    if not stage_script.exists():
        return subprocess.CompletedProcess(args=[str(stage_script)], returncode=127, stdout="", stderr=f"Missing stage script: {stage_script}")

    env = {
        "VMCX_STAGE_ID": stage_id,
        "VMCX_TARGET_ID": str(target.get("target_id", "")),
        "VMCX_EXEC_MODE": "local",
        "VMCX_PARAMS_JSON": json.dumps(params),
        "VMCX_MERGED_CONFIG_JSON": json.dumps(merged_config),
        "VMCX_RUN_DIR": str(run_dir),
        "VMCX_REPO_ROOT": str(repo_root),
    }

    return subprocess.run(
        ["bash", str(stage_script)],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        env={**os.environ, **env},
        check=False,
    )
