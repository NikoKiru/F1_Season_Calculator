"""Playwright e2e — starts a live FastAPI server bound to the seeded test DB.

Run with `pytest tests/e2e` after `playwright install chromium`. Without a browser
these tests skip, except in CI, where a skip would hide a broken job.
"""
from __future__ import annotations

import os
import socket
import threading
import time

import pytest


def _browser_unavailable(reason: str) -> None:
    if os.environ.get("CI"):
        pytest.fail(reason)
    pytest.skip(reason)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def live_server(seeded_settings):
    import uvicorn

    from app.main import create_app

    port = _free_port()
    config = uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)
    assert server.started, "uvicorn failed to start"

    yield f"http://127.0.0.1:{port}"

    server.should_exit = True
    thread.join(timeout=5)


@pytest.fixture(scope="session")
def browser():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _browser_unavailable("playwright not installed")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception as e:
            _browser_unavailable(f"playwright browser unavailable: {e}")
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda exc: errors.append(str(exc)))
    page.on("console", lambda msg: errors.append(msg.text) if msg.type == "error" else None)
    yield page
    context.close()
    # Surface JS errors as test failures.
    assert not errors, f"JS errors on page: {errors}"
