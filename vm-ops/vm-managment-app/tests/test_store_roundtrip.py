#!/usr/bin/env python3
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config_store


class ConfigStoreRoundtripTest(unittest.TestCase):
    def _seed_repo(self, root: Path) -> None:
        (root / "runtime").mkdir(parents=True, exist_ok=True)
        (root / "runtime" / "vmcx").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        cfg = root / "vm-configs"
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "vm-machines.yaml").write_text(
            json.dumps({"machines": {}, "groups": {}}, indent=2) + "\n", encoding="utf-8"
        )
        (cfg / "vm-operations.yaml").write_text(
            json.dumps({"operations": {}}, indent=2) + "\n", encoding="utf-8"
        )
        (cfg / "vm-env-rules.yaml").write_text(
            json.dumps({"rules": {}}, indent=2) + "\n", encoding="utf-8"
        )

    def test_upsert_and_save_machine(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            paths = config_store.get_paths(root)
            bundle = config_store.load_bundle(paths)

            config_store.upsert_machine(
                bundle,
                machine_id="demo-1",
                machine_payload={
                    "type": "vm",
                    "env": "stage",
                    "groups": ["demo"],
                    "enabled_setups": ["vm_install"],
                    "exec_mode": "local",
                    "repo_path": "/opt/vm-ops",
                    "ssh": {"host": "", "user": "", "port": 22, "key_ref": ""},
                    "params": {},
                    "defaults": {},
                },
            )

            config_store.save_bundle(paths, bundle, ["machines"])
            reloaded = config_store.load_bundle(paths)
            machines = reloaded.machines_doc["machines"]

            self.assertIn("demo-1", machines)
            self.assertEqual(machines["demo-1"]["env"], "stage")
            self.assertIn("demo", reloaded.machines_doc["groups"])

    def test_render_diff_detects_changes(self) -> None:
        old_text = "{\n  \"machines\": {}\n}\n"
        new_text = "{\n  \"machines\": {\"a\": {}}\n}\n"
        diff = config_store.render_diff(old_text, new_text, "vm-configs/vm-machines.yaml")
        self.assertIn("vm-configs/vm-machines.yaml", diff)
        self.assertIn("+  \"machines\": {\"a\": {}}", diff)


if __name__ == "__main__":
    unittest.main()
