from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest


class VmcxCliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = Path(__file__).resolve().parents[3]
        cls.vmcx = cls.repo_root / "vm-codex" / "runtime" / "vmcx"

    def run_vmcx(self, args: list[str]) -> dict:
        completed = subprocess.run(
            [str(self.vmcx)] + args,
            cwd=str(self.repo_root),
            capture_output=True,
            text=True,
            check=True,
        )
        return json.loads(completed.stdout)

    def test_alias_plan_returns_expected_target_and_stages(self) -> None:
        out = self.run_vmcx(["plan", "--alias", "n8n-vm-setup"])
        self.assertEqual(out["status"], "planned")
        self.assertEqual(out["target_id"], "n8n-vm")
        self.assertEqual(
            out["stages"],
            ["vm_install", "app_deploy", "cloudflare_vm_access", "cloudflare_app_access"],
        )

    def test_run_without_confirm_blocks(self) -> None:
        out = self.run_vmcx(["run", "--alias", "n8n-vm-setup", "--dry-run"])
        self.assertEqual(out["status"], "blocked")
        self.assertEqual(out["error_class"], "confirmation_required")

    def test_group_dry_run_with_confirm_succeeds(self) -> None:
        out = self.run_vmcx(
            [
                "run-group",
                "--group",
                "app-tier",
                "--stages",
                "vm_install",
                "--concurrency",
                "2",
                "--dry-run",
                "--confirm",
            ]
        )
        self.assertEqual(out["status"], "succeeded")
        self.assertEqual(out["total"], 2)
        self.assertEqual(out["failed"], 0)

    def test_restore_stage_blocks_non_staging(self) -> None:
        out = self.run_vmcx(
            [
                "run",
                "--target",
                "n8n-vm",
                "--stages",
                "restore_app",
                "--params",
                '{"restore_app":{"restore_target_type":"prod"}}',
                "--confirm",
            ]
        )
        self.assertEqual(out["status"], "failed")
        self.assertEqual(out["error_class"], "non_retryable_stage_error")


if __name__ == "__main__":
    unittest.main()
