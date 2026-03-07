#!/usr/bin/env python3
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, Iterable, Optional

from .realtime_bus import RealtimeBus


class ConfigFileWatcher:
    def __init__(self, paths: Iterable[Path], bus: RealtimeBus, interval_sec: float = 1.0) -> None:
        self._paths = [p.resolve() for p in paths]
        self._bus = bus
        self._interval = interval_sec
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._state: Dict[Path, str] = {}

    def _fingerprint(self, path: Path) -> str:
        if not path.exists():
            return "missing"
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        return f"{path.stat().st_mtime_ns}:{digest}"

    def _scan_once(self, initial: bool = False) -> None:
        for path in self._paths:
            current = self._fingerprint(path)
            previous = self._state.get(path)
            self._state[path] = current
            if initial:
                continue
            if previous is None:
                continue
            if previous != current:
                self._bus.publish(
                    "config_changed",
                    {
                        "file": str(path),
                        "version_hint": current,
                    },
                )

    def _loop(self) -> None:
        self._scan_once(initial=True)
        while not self._stop.is_set():
            try:
                self._scan_once(initial=False)
            except Exception as exc:  # noqa: BLE001
                self._bus.publish("watch_error", {"error": str(exc)})
            self._stop.wait(self._interval)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="config-file-watch", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
