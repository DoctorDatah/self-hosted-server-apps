#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.config_management.services.config_store import ConfigBundle
from app.features.config_management.services import validators


class ValidatorsTest(unittest.TestCase):
    def _seed_setups(self, root: Path) -> None:
        for setup_id in ["vm_install", "app_deploy", "backup_app"]:
            path = root / "vm-setups" / setup_id
            path.mkdir(parents=True, exist_ok=True)
            (path / "stage.yaml").write_text("{}\n", encoding="utf-8")

    def test_validate_bundle_success(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_setups(root)

            bundle = ConfigBundle(
                machines_doc={
                    "machines": {
                        "machine-1": {
                            "type": "vm",
                            "env": "stage",
                            "labels": ["n8n"],
                            "groups": ["demo"],
                            "enabled_setups": ["vm_install", "app_deploy"],
                            "exec_mode": "local",
                            "repo_path": "/opt/vm-ops",
                            "ssh": {"host": "", "user": "", "port": 22, "key_ref": ""},
                            "params": {},
                            "defaults": {},
                        }
                    },
                    "groups": {"demo": ["machine-1"]},
                },
                operations_doc={
                    "operations": {
                        "op-1": {
                            "machine": "machine-1",
                            "setups": ["app_deploy"],
                            "params": {},
                            "requires_confirmation": True,
                            "description": "demo",
                        }
                    }
                },
                rules_doc={
                    "rules": {
                        "backup_app": {
                            "allowed_environments": ["stage", "prod"],
                            "requires_confirmation": True,
                        }
                    }
                },
                machines_text="",
                operations_text="",
                rules_text="",
            )

            errors = validators.validate_bundle(bundle, root)
            self.assertEqual(errors, [])

    def test_validate_unknown_machine_reference(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_setups(root)

            bundle = ConfigBundle(
                machines_doc={"machines": {}, "groups": {}},
                operations_doc={
                    "operations": {
                        "op-1": {
                            "machine": "missing",
                            "setups": ["app_deploy"],
                            "params": {},
                            "requires_confirmation": True,
                        }
                    }
                },
                rules_doc={"rules": {}},
                machines_text="",
                operations_text="",
                rules_text="",
            )

            errors = validators.validate_bundle(bundle, root)
            self.assertTrue(any("unknown machine" in e for e in errors))

    def test_validate_ssh_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_setups(root)

            bundle = ConfigBundle(
                machines_doc={
                    "machines": {
                        "ssh-box": {
                            "type": "vm",
                            "env": "prod",
                            "groups": ["prod"],
                            "enabled_setups": ["vm_install"],
                            "exec_mode": "ssh",
                            "repo_path": "/opt/vm-ops",
                            "ssh": {"host": "", "user": "", "port": "bad"},
                            "params": {},
                            "defaults": {},
                        }
                    },
                    "groups": {"prod": ["ssh-box"]},
                },
                operations_doc={"operations": {}},
                rules_doc={"rules": {}},
                machines_text="",
                operations_text="",
                rules_text="",
            )

            errors = validators.validate_bundle(bundle, root)
            self.assertTrue(any("missing ssh.host" in e for e in errors))
            self.assertTrue(any("missing ssh.user" in e for e in errors))
            self.assertTrue(any("invalid ssh.port" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
