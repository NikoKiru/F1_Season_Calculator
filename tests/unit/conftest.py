"""Pytest fixtures — in-memory SQLite seeded by the real pipeline.

Sharing one seeded DB across a pytest session keeps tests < 1s total without
giving up fidelity: the same combinator + writer code that prod uses runs
against a 3-driver × 4-race CSV, so every service sees real rows.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import Connection, create_engine

from app.config import Settings, get_settings
from app.data.schema import init_schema
from app.pipeline import csv_loader, stats_compute, writer
from app.services import season_service


SAMPLE_CSV = """Driver,1,2,3,4
VER,25,18,25,18
NOR,18,25,18,25
LEC,15,15,15,15
"""

SAMPLE_SEASON_JSON = {
    "teams": {
        "Red Bull": {"color": "#3671C6"},
        "McLaren": {"color": "#FF8000"},
        "Ferrari": {"color": "#F91536"},
    },
    "drivers": {
        "VER": {"name": "Max Verstappen", "team": "Red Bull", "number": 1, "flag": "🇳🇱"},
        "NOR": {"name": "Lando Norris", "team": "McLaren", "number": 4, "flag": "🇬🇧"},
        "LEC": {"name": "Charles Leclerc", "team": "Ferrari", "number": 16, "flag": "🇲🇨"},
    },
    "rounds": {"1": "Round 1", "2": "Round 2", "3": "Round 3", "4": "Round 4"},
}

TEST_SEASON = 9999


@pytest.fixture(scope="session")
def test_data_root(tmp_path_factory) -> Path:
    """Create an isolated data + instance dir and seed it via the real pipeline."""
    root = tmp_path_factory.mktemp("f1-tests")
    data = root / "data"
    seasons = data / "seasons"
    instance = root / "instance"
    for d in (data, seasons, instance):
        d.mkdir(parents=True, exist_ok=True)

    (data / f"championships_{TEST_SEASON}.csv").write_text(SAMPLE_CSV)
    (seasons / f"{TEST_SEASON}.json").write_text(json.dumps(SAMPLE_SEASON_JSON))

    db_path = instance / "test.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    with engine.begin() as conn:
        init_schema(conn)
    engine.dispose()

    loaded = csv_loader.load(data / f"championships_{TEST_SEASON}.csv")
    writer.process_season(db_path, loaded, season=TEST_SEASON, batch_size=5)
    stats_compute.compute(db_path, TEST_SEASON)

    return root


@pytest.fixture(scope="session")
def seeded_settings(test_data_root: Path, monkeypatch_session) -> Settings:
    """Swap the module-level settings to point at the isolated tree."""
    test_settings = Settings(
        database_path=test_data_root / "instance" / "test.db",
        data_folder=test_data_root / "data",
        seasons_folder=test_data_root / "data" / "seasons",
        default_season=TEST_SEASON,
    )
    import app.config as config_mod
    monkeypatch_session.setattr(config_mod, "get_settings", lambda: test_settings)
    # Patch every already-bound reference.
    for module_name in (
        "app.data.session",
        "app.cache.service",
        "app.services.season_service",
        "app.services.championship_service",
        "app.templating",
        "app.main",
    ):
        try:
            mod = __import__(module_name, fromlist=["get_settings"])
        except ImportError:
            continue
        if hasattr(mod, "get_settings"):
            monkeypatch_session.setattr(mod, "get_settings", lambda: test_settings)
    season_service.clear_cache()
    yield test_settings
    season_service.clear_cache()


@pytest.fixture(scope="session")
def monkeypatch_session():
    # pytest's monkeypatch is function-scoped; this is the standard session-scoped variant
    from _pytest.monkeypatch import MonkeyPatch
    mp = MonkeyPatch()
    yield mp
    mp.undo()


@pytest.fixture
def conn(seeded_settings: Settings) -> Connection:
    from app.data.engine import get_engine

    engine = get_engine(seeded_settings.database_path)
    with engine.connect() as c:
        yield c
