#!/usr/bin/env python3
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from ...core.app_meta import APP_DISPLAY_NAME
from .service import ui_system_template_dirs

router = APIRouter(tags=["ui-system"])
templates = Jinja2Templates(directory=ui_system_template_dirs())


@router.get("/")
def home(request: Request):
    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "page_title": "Home",
            "app_display_name": APP_DISPLAY_NAME,
            "nav_mode": "home",
        },
    )


@router.get("/features")
def features_home() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)


@router.get("/features/ui-system")
def ui_system_page() -> RedirectResponse:
    return RedirectResponse(url="/", status_code=307)
