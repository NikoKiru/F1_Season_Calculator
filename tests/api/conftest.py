"""API test fixtures — FastAPI TestClient bound to the seeded test DB.

Session-scoped seeding fixtures live in tests/conftest.py (root conftest)
so they're visible here without `pytest_plugins` indirection.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.cache import service as cache


@pytest.fixture
def client(seeded_settings):
    cache.clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
    cache.clear()
