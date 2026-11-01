"""Vite hashes every file under dist/assets, so only those can be cached for good."""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

HASHED_ASSET = "/static/dist/assets/main-abc123.js"


@pytest.fixture
def static_client(seeded_settings, tmp_path: Path, monkeypatch):
    assets = tmp_path / "dist" / "assets"
    assets.mkdir(parents=True)
    (assets / "main-abc123.js").write_text("export {};", encoding="utf-8")
    (tmp_path / "dist" / "manifest.json").write_text("{}", encoding="utf-8")
    (tmp_path / "flags").mkdir()
    (tmp_path / "flags" / "gb.svg").write_text("<svg/>", encoding="utf-8")

    settings = seeded_settings.model_copy(update={"static_folder": tmp_path})
    monkeypatch.setattr("app.main.get_settings", lambda: settings)

    from app.main import create_app

    with TestClient(create_app()) as client:
        yield client


def test_hashed_assets_are_cached_for_a_year(static_client):
    response = static_client.get(HASHED_ASSET)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=31536000, immutable"


def test_revalidating_a_hashed_asset_keeps_the_cache_header(static_client):
    etag = static_client.get(HASHED_ASSET).headers["etag"]
    response = static_client.get(HASHED_ASSET, headers={"If-None-Match": etag})
    assert response.status_code == 304
    assert "immutable" in response.headers["cache-control"]


@pytest.mark.parametrize("path", ["/static/dist/manifest.json", "/static/flags/gb.svg"])
def test_files_without_a_hash_are_not_cached_for_good(static_client, path):
    response = static_client.get(path)
    assert response.status_code == 200
    assert "immutable" not in response.headers.get("cache-control", "")
