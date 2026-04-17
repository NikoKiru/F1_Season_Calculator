"""Jinja2 environment + Vite manifest asset resolver.

At build time Vite emits `app/static/dist/manifest.json`; we read it once at
startup and expose `vite_asset(name)` as a Jinja global so templates can ask
for asset URLs by their input path (e.g. `web/src/pages/driver.ts`) without
any runtime filesystem lookups on render.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import Request
from fastapi.templating import Jinja2Templates
from markupsafe import Markup

from app.config import get_settings


def _manifest_path() -> Path:
    return get_settings().static_dist_folder / "manifest.json"


@lru_cache(maxsize=1)
def _manifest() -> dict[str, dict]:
    path = _manifest_path()
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _asset_url(path: str) -> str:
    """Resolve an input path (relative to the Vite root) to its hashed URL."""
    manifest = _manifest()
    entry = manifest.get(path)
    if not entry:
        # Dev fallback: point straight at the source. The Vite dev server
        # would normally serve these; without it, browser requests 404 but
        # the page still renders.
        return f"/static/dist/{path}"
    return f"/static/dist/{entry['file']}"


def _asset_script(path: str) -> Markup:
    entry = _manifest().get(path)
    url = _asset_url(path)
    tags = [f'<script type="module" src="{url}" defer></script>']
    if entry:
        for css in entry.get("css", []):
            tags.append(f'<link rel="stylesheet" href="/static/dist/{css}">')
        for imp in entry.get("imports", []):
            dep = _manifest().get(imp)
            if dep:
                tags.append(f'<link rel="modulepreload" href="/static/dist/{dep["file"]}">')
    return Markup("\n    ".join(tags))


def _asset_style(path: str) -> Markup:
    entry = _manifest().get(path)
    if entry:
        return Markup(f'<link rel="stylesheet" href="/static/dist/{entry["file"]}">')
    return Markup(f'<link rel="stylesheet" href="/static/dist/{path}">')


templates = Jinja2Templates(directory=str(get_settings().templates_folder))
templates.env.globals["vite_script"] = _asset_script
templates.env.globals["vite_style"] = _asset_style
templates.env.globals["vite_asset"] = _asset_url


def render(request: Request, template: str, context: dict, *, status_code: int = 200):
    return templates.TemplateResponse(request, template, context, status_code=status_code)
