#!/usr/bin/env python3
import sys
import tempfile
import unittest
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.features.config_management.services import settings


class SettingsTest(unittest.TestCase):
    def test_default_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            cfg = settings.load_settings(root)
            self.assertEqual(cfg["timezone"], "UTC")
            self.assertEqual(cfg["preferred_config_branch"], "")

    def test_save_and_load_timezone(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            saved = settings.save_settings(
                root,
                timezone_name="America/Toronto",
                preferred_config_branch="config_update/March-07-2026--11-00-AM",
            )
            self.assertEqual(saved["timezone"], "America/Toronto")
            self.assertEqual(settings.get_timezone(root), "America/Toronto")
            self.assertEqual(settings.get_preferred_config_branch(root), "config_update/March-07-2026--11-00-AM")

    def test_format_iso_datetime(self) -> None:
        out = settings.format_iso_datetime("2026-03-07T12:30:00+00:00", "America/Toronto")
        self.assertIn("2026-03-07", out)
        self.assertTrue("EST" in out or "EDT" in out)

    def test_timezone_list_includes_utc(self) -> None:
        zones = settings.all_timezones()
        self.assertIn("UTC", zones)

    def test_old_branch_name_auto_migrates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_data = root / "vm-managment-app" / "app-data"
            app_data.mkdir(parents=True, exist_ok=True)
            settings_file = app_data / "settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "timezone": "UTC",
                        "preferred_config_branch": "config_update/update-20260307-005609",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            loaded = settings.load_settings(root)
            self.assertEqual(
                loaded["preferred_config_branch"],
                "config_update/March-07-2026--12-56-AM",
            )

    def test_new_branch_name_without_meridiem_separator_migrates(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            app_data = root / "vm-managment-app" / "app-data"
            app_data.mkdir(parents=True, exist_ok=True)
            settings_file = app_data / "settings.json"
            settings_file.write_text(
                json.dumps(
                    {
                        "timezone": "UTC",
                        "preferred_config_branch": "config_update/March-07-2026--01-18AM",
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            loaded = settings.load_settings(root)
            self.assertEqual(loaded["preferred_config_branch"], "config_update/March-07-2026--01-18-AM")


if __name__ == "__main__":
    unittest.main()
