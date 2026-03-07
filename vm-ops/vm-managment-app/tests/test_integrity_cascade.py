#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.config_management.services.cascade import preview_cascade
from app.features.config_management.services.config_store import ConfigBundle
from app.features.config_management.services.integrity import build_delete_impact_report


class IntegrityCascadeTest(unittest.TestCase):
    def _seed_setups(self, root: Path) -> None:
        for setup_id in ["vm_install", "app_deploy", "backup_app"]:
            setup_dir = root / "vm-setups" / setup_id
            setup_dir.mkdir(parents=True, exist_ok=True)
            (setup_dir / "stage.yaml").write_text("{}\n", encoding="utf-8")

    def _bundle(self) -> ConfigBundle:
        return ConfigBundle(
            machines_doc={
                "machines": {
                    "m1": {
                        "env": "stage",
                        "groups": ["g1"],
                        "enabled_setups": ["vm_install", "app_deploy"],
                        "exec_mode": "local",
                        "ssh": {"host": "", "user": "", "port": 22, "key_ref": ""},
                        "params": {},
                        "defaults": {},
                    }
                },
                "groups": {"g1": ["m1"]},
            },
            operations_doc={
                "operations": {
                    "op1": {
                        "machine": "m1",
                        "setups": ["app_deploy"],
                        "params": {},
                        "requires_confirmation": True,
                    }
                }
            },
            rules_doc={"rules": {"backup_app": {"requires_confirmation": True}}},
            machines_text="",
            operations_text="",
            rules_text="",
        )

    def test_machine_delete_reports_blocker(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_setups(root)
            report = build_delete_impact_report(self._bundle(), root, "machine", "m1")
            self.assertTrue(report.blockers)
            self.assertEqual(report.cascade_plan.removed_machines, ["m1"])
            self.assertIn("op1", report.cascade_plan.removed_operations)

    def test_cascade_true_removes_machine_and_operation(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_setups(root)

            candidate, parts, _errors, report = preview_cascade(
                self._bundle(), root, entity_type="machine", entity_id="m1", cascade=True
            )
            self.assertIn("machines", parts)
            self.assertIn("operations", parts)
            self.assertNotIn("m1", candidate.machines_doc["machines"])
            self.assertNotIn("op1", candidate.operations_doc["operations"])
            self.assertTrue(report.blockers)


if __name__ == "__main__":
    unittest.main()
