#!/usr/bin/env python3
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .routes_api import router as api_router
from .routes_ui import router as ui_router

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

app = FastAPI(title="vm-managment-app", version="0.1.0")
app.mount("/static", StaticFiles(directory=str(PROJECT_DIR / "static")), name="static")

app.include_router(ui_router)
app.include_router(api_router)
