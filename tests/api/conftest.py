"""API test fixtures — FastAPI TestClient bound to the seeded test DB."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.cache import service as cache


# Reuse the session-scoped seeding from tests/unit/conftest.py
pytest_plugins = ["tests.unit.conftest"]


@pytest.fixture
def client(seeded_settings):
    cache.clear()
    from app.main import create_app

    app = create_app()
    with TestClient(app) as c:
        yield c
    cache.clear()
