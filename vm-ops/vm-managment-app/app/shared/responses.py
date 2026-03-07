#!/usr/bin/env python3
from typing import Any, Dict, Optional


def ok(data: Optional[Dict[str, Any]] = None, **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {"ok": True}
    if data:
        payload.update(data)
    payload.update(extra)
    return payload


def err(message: str, code: str = "error", **extra: Any) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
        },
    }
    if extra:
        payload["error"].update(extra)
    return payload
