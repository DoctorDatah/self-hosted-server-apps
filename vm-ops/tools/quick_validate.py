#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def find_repo_root(start: Path) -> Path:
    current = start.resolve()
    for candidate in [current] + list(current.parents):
        if (candidate / "runtime" / "vmcx").exists():
            return candidate
    raise FileNotFoundError("Could not locate runtime/vmcx from tools/quick_validate.py")


def main() -> int:
    repo_root = find_repo_root(Path(__file__).parent)
    cmd = [str(repo_root / "runtime" / "vmcx"), "doctor", "--ci"]
    proc = subprocess.run(cmd, cwd=repo_root, text=True)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
