#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import git_ops


class GitOpsTest(unittest.TestCase):
    def _run(self, root: Path, args):
        proc = subprocess.run(args, cwd=root, check=True, capture_output=True, text=True)
        return proc.stdout.strip()

    def _seed_repo(self, root: Path) -> None:
        self._run(root, ["git", "init"]) 
        self._run(root, ["git", "config", "user.email", "test@example.com"])
        self._run(root, ["git", "config", "user.name", "VM Config Test"])

        cfg = root / "vm-configs"
        cfg.mkdir(parents=True, exist_ok=True)
        for name, payload in [
            ("vm-machines.yaml", {"machines": {}, "groups": {}}),
            ("vm-operations.yaml", {"operations": {}}),
            ("vm-env-rules.yaml", {"rules": {}}),
        ]:
            (cfg / name).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

        self._run(root, ["git", "add", "."])
        self._run(root, ["git", "commit", "-m", "init"])

    def test_prepare_commit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)

            machines = root / "vm-configs" / "vm-machines.yaml"
            machines.write_text(
                json.dumps(
                    {
                        "machines": {
                            "m1": {
                                "env": "stage",
                                "enabled_setups": ["vm_install"],
                                "exec_mode": "local",
                            }
                        },
                        "groups": {},
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            result = git_ops.prepare_commit(
                root,
                tracked_files=[
                    "vm-configs/vm-machines.yaml",
                    "vm-configs/vm-operations.yaml",
                    "vm-configs/vm-env-rules.yaml",
                ],
            )

            self.assertTrue(result["branch"].startswith("config_update/update-"))
            self.assertTrue(result["commit_sha"])
            self.assertIn("vm-configs/vm-machines.yaml", result["changed_files"])

    def test_switch_and_push_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            root.mkdir(parents=True, exist_ok=True)
            self._seed_repo(root)

            remote = Path(td) / "remote.git"
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True, text=True)
            self._run(root, ["git", "remote", "add", "origin", str(remote)])

            initial_branch = git_ops.current_branch(root)
            switched = git_ops.switch_branch(root, "ui-managed-branch")
            self.assertEqual(switched["branch"], "ui-managed-branch")
            # UI target branch should not checkout/switch the main local branch.
            self.assertEqual(git_ops.current_branch(root), initial_branch)

            pushed = git_ops.push_branch(root, branch_name="ui-managed-branch", remote_name="origin", set_upstream=True)
            self.assertEqual(pushed["branch"], "ui-managed-branch")
            self.assertEqual(pushed["remote"], "origin")

            remote_heads = subprocess.run(
                ["git", "ls-remote", "--heads", str(remote), "ui-managed-branch"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertTrue(remote_heads)

    def test_prepare_commit_reuses_existing_related_branch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)

            existing = "config_update/update-20260307-120000"
            self._run(root, ["git", "branch", existing])

            machines = root / "vm-configs" / "vm-machines.yaml"
            machines.write_text(
                json.dumps({"machines": {"m2": {"env": "dev"}}, "groups": {}}, indent=2) + "\n",
                encoding="utf-8",
            )

            result = git_ops.prepare_commit(
                root,
                tracked_files=[
                    "vm-configs/vm-machines.yaml",
                    "vm-configs/vm-operations.yaml",
                    "vm-configs/vm-env-rules.yaml",
                ],
                preferred_branch="",
                fallback_tz="UTC",
            )
            self.assertEqual(result["branch"], existing)


if __name__ == "__main__":
    unittest.main()
