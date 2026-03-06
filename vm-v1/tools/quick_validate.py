#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    cmd = [str(repo_root / "runtime" / "vmcx"), "doctor", "--ci"]
    proc = subprocess.run(cmd, cwd=repo_root, text=True)
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
