"""The server keeps running while builds and syncs change its files.

`npm run build`, `f1 sync` and a rebuild all run in other processes, so the
files are the only signal the server gets. Each test changes a file the way
those tools do and checks that the next read sees it, with no restart.
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import pytest
from sqlalchemy import text

from app import templating
from app.cache import service as cache_service
from app.config import Settings
from app.data.engine import dispose_engine, get_engine
from app.services import driver_service, season_service

SEASON = 7777


def _touch_later(path: Path) -> None:
    """Move a modified time forward: tests write faster than the filesystem clock ticks."""
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))


def _write_season(settings: Settings, year: int, team: str = "Red Bull") -> Path:
    path = settings.seasons_folder / f"{year}.json"
    path.write_text(
        json.dumps({"teams": {team: {"color": "#111111"}}, "drivers": {}, "rounds": {"1": "AUS"}}),
        encoding="utf-8",
    )
    return path


@pytest.fixture
def settings(tmp_path: Path, monkeypatch):
    seasons = tmp_path / "data" / "seasons"
    seasons.mkdir(parents=True)
    isolated = Settings(
        database_path=tmp_path / "live.db",
        data_folder=tmp_path / "data",
        seasons_folder=seasons,
        default_season=SEASON,
    )
    monkeypatch.setattr(season_service, "get_settings", lambda: isolated)
    monkeypatch.setattr(cache_service, "get_settings", lambda: isolated)
    monkeypatch.setattr(cache_service, "_cache", None)
    season_service.clear_cache()
    yield isolated
    season_service.clear_cache()
    dispose_engine(isolated.database_path)


# --- Vite manifest ----------------------------------------------------------


def test_new_build_is_served_without_a_restart(tmp_path: Path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    monkeypatch.setattr(templating, "_manifest_path", lambda: manifest)

    manifest.write_text(json.dumps({"src/main.ts": {"file": "assets/main-old.js"}}), encoding="utf-8")
    assert templating._asset_url("src/main.ts") == "/static/dist/assets/main-old.js"

    manifest.write_text(json.dumps({"src/main.ts": {"file": "assets/main-new.js"}}), encoding="utf-8")
    _touch_later(manifest)
    assert templating._asset_url("src/main.ts") == "/static/dist/assets/main-new.js"


def test_missing_manifest_falls_back_to_the_source_path(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(templating, "_manifest_path", lambda: tmp_path / "absent.json")
    assert templating._asset_url("src/main.ts") == "/static/dist/src/main.ts"


def test_manifest_caught_mid_write_falls_back_to_the_source_path(tmp_path: Path, monkeypatch):
    manifest = tmp_path / "manifest.json"
    manifest.write_text('{"src/main.ts": {"fi', encoding="utf-8")
    monkeypatch.setattr(templating, "_manifest_path", lambda: manifest)
    assert templating._asset_url("src/main.ts") == "/static/dist/src/main.ts"


# --- Season JSON ------------------------------------------------------------


def test_season_json_edit_is_served_without_a_restart(settings):
    path = _write_season(settings, SEASON, team="Old Team")
    assert "Old Team" in season_service.get_season_data(SEASON).teams

    _write_season(settings, SEASON, team="New Team")
    _touch_later(path)
    assert "New Team" in season_service.get_season_data(SEASON).teams


def test_unchanged_season_json_is_not_parsed_again(settings):
    _write_season(settings, SEASON)
    assert season_service.get_season_data(SEASON) is season_service.get_season_data(SEASON)


def test_new_season_file_appears_without_a_restart(settings):
    _write_season(settings, SEASON)
    assert season_service.available_seasons() == (SEASON,)

    _write_season(settings, SEASON + 1)
    _touch_later(settings.seasons_folder)
    assert season_service.available_seasons() == (SEASON + 1, SEASON)


def test_renamed_team_resolves_without_a_restart(settings):
    path = _write_season(settings, SEASON, team="Old Team")
    assert season_service.resolve_team_slug("old-team", SEASON) == "Old Team"

    _write_season(settings, SEASON, team="New Team")
    _touch_later(path)
    assert season_service.resolve_team_slug("new-team", SEASON) == "New Team"


# --- Service cache ----------------------------------------------------------


def _remember(value: str) -> str:
    """What the cache holds for one key, computing `value` only if it holds nothing."""
    return cache_service.get_or_compute("key", lambda: value)


def _seed_database(settings: Settings):
    engine = get_engine(settings.database_path)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (x INTEGER)"))
        conn.execute(text("INSERT INTO t VALUES (1)"))
    return engine


def test_reading_the_database_keeps_cached_results(settings):
    """The server's own reads must not look like a rebuild, or nothing stays cached."""
    engine = _seed_database(settings)
    _remember("cached")
    for _ in range(5):
        with engine.connect() as conn:
            conn.execute(text("SELECT x FROM t")).fetchall()
        assert _remember("recomputed") == "cached"


def test_commit_from_another_process_clears_cached_results(settings):
    """A rebuild writes through its own connection while the server's pool stays open."""
    engine = _seed_database(settings)
    with engine.connect() as conn:
        conn.execute(text("SELECT x FROM t")).fetchall()
    _remember("cached")

    rebuild = sqlite3.connect(settings.database_path)
    rebuild.execute("INSERT INTO t VALUES (2)")
    rebuild.commit()
    rebuild.close()

    assert _remember("recomputed") == "recomputed"


def test_season_json_edit_clears_cached_results(settings):
    path = _write_season(settings, SEASON)
    _remember("cached")

    _touch_later(path)
    assert _remember("recomputed") == "recomputed"


def test_result_computed_during_a_rebuild_is_not_kept(settings):
    settings.database_path.write_bytes(b"database")

    def compute() -> str:
        # The rebuild commits while this result is being read.
        _touch_later(settings.database_path)
        return "half built"

    assert cache_service.get_or_compute("key", compute) == "half built"
    assert _remember("recomputed") == "recomputed"


def test_service_result_computed_during_a_rebuild_is_not_kept(settings, monkeypatch):
    settings.database_path.write_bytes(b"database")
    answers = iter([(1, 2), (3, 4)])

    def head_to_head_pair(_conn, _a, _b, _season) -> tuple[int, int]:
        _touch_later(settings.database_path)
        return next(answers)

    monkeypatch.setattr(driver_service.q_d, "head_to_head_pair", head_to_head_pair)

    assert driver_service.head_to_head(None, "NOR", "VER", SEASON) == {"NOR": 1, "VER": 2}
    assert driver_service.head_to_head(None, "NOR", "VER", SEASON) == {"NOR": 3, "VER": 4}
