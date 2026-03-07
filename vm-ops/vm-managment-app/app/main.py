#!/usr/bin/env python3
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .core.app_meta import APP_DISPLAY_NAME, APP_VERSION
from .core.file_watch import ConfigFileWatcher
from .core.realtime_bus import bus
from .features.config_management.routes_api import router as config_api_router
from .features.config_management.routes_ui import router as config_ui_router
from .features.config_management.services import config_store
from .features.ui_system.routes import router as ui_system_router
from .features.ui_system.service import config_static_dir, ui_static_dir

APP_DIR = Path(__file__).resolve().parent

app = FastAPI(title=APP_DISPLAY_NAME, version=APP_VERSION)
app.mount("/static", StaticFiles(directory=str(ui_static_dir())), name="static")
app.mount("/static/config", StaticFiles(directory=str(config_static_dir())), name="static-config")

app.include_router(ui_system_router)
app.include_router(config_ui_router)
app.include_router(config_api_router)


@app.on_event("startup")
def _startup_watchers() -> None:
    paths = config_store.get_paths()
    watcher = ConfigFileWatcher(
        [paths.machines_path, paths.operations_path, paths.rules_path],
        bus=bus,
        interval_sec=1.0,
    )
    watcher.start()
    app.state.config_watcher = watcher


@app.on_event("shutdown")
def _shutdown_watchers() -> None:
    watcher = getattr(app.state, "config_watcher", None)
    if watcher is not None:
        watcher.stop()
