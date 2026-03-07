# VM Management Architecture Map

This file exists for humans and AI agents to quickly find where to work.

## 1) Entry Point

- `app/main.py`
  - FastAPI app assembly
  - static mounts
  - router registration
  - startup/shutdown watcher lifecycle

## 2) Core Layer (`app/core/`)

- `app_meta.py`
  - app name/version constants
- `realtime_bus.py`
  - in-memory event bus for SSE
- `file_watch.py`
  - watches config files and publishes `config_changed`
- `dependency_graph.py`
  - relationship graph for integrity analysis

## 3) Shared Layer (`app/shared/`)

- `schemas.py`
  - typed models (integrity reports, cascade plan, API payloads)
- `responses.py`
  - API response helpers

## 4) Feature: UI System (`app/features/ui_system/`)

- `routes.py`
  - feature index + UI system page
- `service.py`
  - theme/layout tokens + template/static path helpers
- `templates/`
  - base shell, features page, ui-system page
- `static/`
  - `css/app.css`, `js/app.js`

## 5) Feature: Config Management (`app/features/config_management/`)

- `routes_ui.py`
  - dashboard + tables + forms pages
  - keeps old URL compatibility (`/machines`, `/operations`, `/rules`)
- `routes_api.py`
  - status/git endpoints
  - integrity endpoints
  - realtime SSE endpoint
- `services/config_store.py`
  - load/save/diff/atomic-write config data
- `services/validators.py`
  - config validations
- `services/integrity.py`
  - dependency and blocker analysis
- `services/cascade.py`
  - deterministic cascade preview/apply logic
- `templates/`
  - config pages and partial forms

## 6) Compatibility Shims

Compatibility shims were removed.

Use feature modules directly for all new imports:
- `app/features/config_management/...`
- `app/features/ui_system/...`
