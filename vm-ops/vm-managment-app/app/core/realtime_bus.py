#!/usr/bin/env python3
import threading
import time
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RealtimeEvent:
    event: str
    version: int
    timestamp: float
    data: Dict[str, Any]


class RealtimeBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._version = 0
        self._latest: RealtimeEvent = RealtimeEvent(
            event="ready",
            version=0,
            timestamp=time.time(),
            data={"message": "bus-ready"},
        )

    def publish(self, event: str, data: Dict[str, Any]) -> RealtimeEvent:
        with self._lock:
            self._version += 1
            self._latest = RealtimeEvent(
                event=event,
                version=self._version,
                timestamp=time.time(),
                data=data,
            )
            return self._latest

    def snapshot(self) -> RealtimeEvent:
        with self._lock:
            return RealtimeEvent(
                event=self._latest.event,
                version=self._latest.version,
                timestamp=self._latest.timestamp,
                data=dict(self._latest.data),
            )


bus = RealtimeBus()
