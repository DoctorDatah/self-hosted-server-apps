#!/usr/bin/env python3
from pathlib import Path
from typing import Dict

APP_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = APP_DIR.parent

UI_TOKENS: Dict[str, object] = {
    "brand": {
        "display_name": "VM Management",
        "subtitle": "Local config and operations control",
    },
    "theme": {
        "primary": "#12c2a4",
        "secondary": "#ffa64d",
        "danger": "#ff5d5d",
        "background_start": "#0c1f2e",
        "background_end": "#122e3f",
    },
    "typography": {
        "body": "IBM Plex Sans",
        "mono": "IBM Plex Mono",
    },
    "layout": {
        "nav_mode": "left_nav",
        "content_density": "comfortable",
    },
}


def ui_system_template_dirs() -> list[str]:
    return [
        str(APP_DIR / "features" / "ui_system" / "templates"),
        str(APP_DIR / "features" / "config_management" / "templates"),
    ]


def ui_static_dir() -> Path:
    return APP_DIR / "features" / "ui_system" / "static"


def config_static_dir() -> Path:
    return APP_DIR / "features" / "config_management" / "static"


def get_ui_tokens() -> Dict[str, object]:
    return UI_TOKENS
