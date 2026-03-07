#!/usr/bin/env python3
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.realtime_bus import RealtimeBus


class RealtimeBusTest(unittest.TestCase):
    def test_publish_increments_version(self) -> None:
        bus = RealtimeBus()
        snap1 = bus.snapshot()
        event = bus.publish("config_changed", {"files": ["a"]})
        snap2 = bus.snapshot()

        self.assertGreater(event.version, snap1.version)
        self.assertEqual(snap2.version, event.version)
        self.assertEqual(snap2.event, "config_changed")


if __name__ == "__main__":
    unittest.main()
