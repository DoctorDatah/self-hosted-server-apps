#!/usr/bin/env python3
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.config_management.services import backups, config_store


class BackupsTest(unittest.TestCase):
    def _seed_repo(self, root: Path) -> None:
        (root / "runtime").mkdir(parents=True, exist_ok=True)
        (root / "runtime" / "vmcx").write_text("#!/usr/bin/env bash\n", encoding="utf-8")
        cfg = root / "vm-configs"
        cfg.mkdir(parents=True, exist_ok=True)

        (cfg / "vm-machines.yaml").write_text(
            json.dumps(
                {
                    "machines": {
                        "m-1": {
                            "type": "app-vm",
                            "env": "stage",
                            "enabled_setups": ["vm_install"],
                            "exec_mode": "local",
                            "repo_path": "/opt/vm-ops",
                            "ssh": {"host": "", "user": "", "port": 22, "key_ref": ""},
                            "groups": ["demo"],
                        }
                    },
                    "groups": {"demo": ["m-1"]},
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (cfg / "vm-operations.yaml").write_text(
            json.dumps({"operations": {"op-1": {"machine": "m-1", "setups": ["vm_install"], "params": {}}}}, indent=2)
            + "\n",
            encoding="utf-8",
        )
        (cfg / "vm-env-rules.yaml").write_text(
            json.dumps({"rules": {"vm_install": {"requires_confirmation": True}}}, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_create_list_restore(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            paths = config_store.get_paths(root)

            original = paths.machines_path.read_text(encoding="utf-8")

            meta = backups.create_backup(paths, label="before-change", remark="test backup")
            self.assertTrue(meta["backup_id"].startswith("cfg-"))
            self.assertRegex(meta["backup_id"], r"^cfg-[A-Za-z]+-\d{2}-\d{4}--\d{2}-\d{2}-[AP]M-[0-9a-f]{6}$")
            self.assertEqual(meta["label"], "before-change")
            self.assertEqual(meta["remark"], "test backup")

            listing = backups.list_backups(paths)
            self.assertEqual(len(listing), 1)
            self.assertEqual(listing[0]["backup_id"], meta["backup_id"])

            paths.machines_path.write_text(
                json.dumps({"machines": {}, "groups": {}}, indent=2) + "\n",
                encoding="utf-8",
            )

            restored = backups.restore_backup(paths, meta["backup_id"])
            self.assertIn("vm-configs/vm-machines.yaml", restored["restored_files"])
            self.assertEqual(paths.machines_path.read_text(encoding="utf-8"), original)

    def test_filters_and_delete(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            paths = config_store.get_paths(root)

            b1 = backups.create_backup(paths, label="first", remark="alpha")
            b2 = backups.create_backup(paths, label="second", remark="beta")

            all_items = backups.list_backups(paths)
            self.assertGreaterEqual(len(all_items), 2)

            by_label = backups.list_backups(paths, label_query="second")
            self.assertEqual(len(by_label), 1)
            self.assertEqual(by_label[0]["backup_id"], b2["backup_id"])

            last_one = backups.list_backups(paths, last_n=1)
            self.assertEqual(len(last_one), 1)

            exact_day = b1["created_at"][:10]
            by_date = backups.list_backups(paths, date_exact=exact_day)
            self.assertGreaterEqual(len(by_date), 2)

            deleted = backups.delete_backup(paths, b1["backup_id"])
            self.assertEqual(deleted["backup_id"], b1["backup_id"])
            remaining_ids = [x["backup_id"] for x in backups.list_backups(paths)]
            self.assertNotIn(b1["backup_id"], remaining_ids)

    def test_backup_status_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._seed_repo(root)
            paths = config_store.get_paths(root)

            s0 = backups.get_backup_status(paths)
            self.assertEqual(s0["state"], "not_backed_up")

            created = backups.create_backup(paths, label="baseline", remark="initial")
            self.assertTrue(created.get("config_fingerprint"))

            s1 = backups.get_backup_status(paths)
            self.assertEqual(s1["state"], "backed_up")
            self.assertEqual(s1["latest_matching_backup_id"], created["backup_id"])

            # Mutate config after backup, status should no longer be backed up.
            doc = json.loads(paths.machines_path.read_text(encoding="utf-8"))
            doc["machines"]["m-1"]["env"] = "prod"
            paths.machines_path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
            s2 = backups.get_backup_status(paths)
            self.assertEqual(s2["state"], "not_backed_up")

            backups.restore_backup(paths, created["backup_id"])
            s3 = backups.get_backup_status(paths)
            self.assertEqual(s3["state"], "backed_up_restored")
            self.assertEqual(s3["last_restore_backup_id"], created["backup_id"])


if __name__ == "__main__":
    unittest.main()
