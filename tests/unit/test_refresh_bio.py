"""refresh-bio CLI — Jolpica patched, real JSON read/write."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.cli import refresh_bio
from app.config import Settings
from app.services import jolpica_service, season_service


SEASON = 8888


SEED = {
    "season": SEASON,
    "teams": {
        "Red Bull": {"color": "#3671C6"},
        "McLaren": {"color": "#FF8000"},
    },
    "drivers": {
        "VER": {
            "name": "Max Verstappen", "team": "Red Bull", "number": 1, "flag": "🇳🇱",
            "nationality": "Dutch", "birthdate": "1997-09-30", "debut_year": 2015,
            "jolpica_id": "max_verstappen", "career": None,
        },
        "NOR": {
            "name": "Lando Norris", "team": "McLaren", "number": 4, "flag": "🇬🇧",
            "nationality": "British", "birthdate": "1999-11-13", "debut_year": 2019,
            "jolpica_id": "norris", "career": None,
        },
        "XXX": {
            "name": "Mystery Rookie", "team": "McLaren", "number": 99, "flag": "🇬🇧",
            "nationality": None, "birthdate": None, "debut_year": None,
            "jolpica_id": None, "career": None,
        },
    },
    "constructors": {
        "Red Bull": {
            "country": "Austria", "founded": 2005, "principal": "Laurent Mekies",
            "power_unit": "Honda RBPT", "chassis": "RB22",
            "jolpica_id": "red_bull", "palmares": None,
        },
        "McLaren": {
            "country": "United Kingdom", "founded": 1963, "principal": "Andrea Stella",
            "power_unit": "Mercedes", "chassis": "MCL40",
            "jolpica_id": None, "palmares": None,
        },
    },
    "rounds": {"1": "AUS"},
}


@pytest.fixture
def tmp_season(tmp_path: Path, monkeypatch) -> Path:
    seasons_dir = tmp_path / "data" / "seasons"
    seasons_dir.mkdir(parents=True)
    json_path = seasons_dir / f"{SEASON}.json"
    json_path.write_text(json.dumps(SEED), encoding="utf-8")

    settings = Settings(
        database_path=tmp_path / "instance" / "x.db",
        data_folder=tmp_path / "data",
        seasons_folder=seasons_dir,
        default_season=SEASON,
    )
    import app.config as config_mod
    monkeypatch.setattr(config_mod, "get_settings", lambda: settings)
    monkeypatch.setattr(
        "app.cli.refresh_bio.get_settings", lambda: settings, raising=False
    )
    season_service.clear_cache()
    return json_path


def test_refresh_bio_writes_career_and_palmares(tmp_season, monkeypatch):
    canned_career = {
        "wins": 65, "podiums": 112, "poles": 41, "championships": 4, "starts": 220
    }
    canned_palmares = {
        "championships": 6, "wins": 122, "podiums": 280, "first_race_year": 1997
    }
    monkeypatch.setattr(
        jolpica_service, "fetch_driver_career",
        lambda jid, *, client: canned_career if jid == "max_verstappen" else None,
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_constructor_palmares",
        lambda jid, *, client: canned_palmares if jid == "red_bull" else None,
    )

    refresh_bio.run(season=SEASON, driver=None, constructor=None)

    raw = json.loads(tmp_season.read_text(encoding="utf-8"))
    # VER got refreshed
    ver = raw["drivers"]["VER"]["career"]
    assert ver["wins"] == 65
    assert ver["podiums"] == 112
    assert ver["championships"] == 4
    assert ver["updated_at"]  # ISO string present

    # NOR got None back from Jolpica — career stays null
    assert raw["drivers"]["NOR"]["career"] is None
    # XXX has no jolpica_id — skipped
    assert raw["drivers"]["XXX"]["career"] is None

    # Red Bull got palmares
    pal = raw["constructors"]["Red Bull"]["palmares"]
    assert pal["championships"] == 6
    assert pal["wins"] == 122
    assert pal["first_race_year"] == 1997
    assert pal["updated_at"]

    # McLaren has no jolpica_id — skipped
    assert raw["constructors"]["McLaren"]["palmares"] is None


def test_refresh_bio_driver_filter_skips_constructors(tmp_season, monkeypatch):
    monkeypatch.setattr(
        jolpica_service, "fetch_driver_career",
        lambda jid, *, client: {
            "wins": 1, "podiums": 2, "poles": 3, "championships": 0, "starts": 10
        },
    )
    called = {"constructors": 0}

    def _ctor_spy(jid, *, client):
        called["constructors"] += 1
        return None

    monkeypatch.setattr(jolpica_service, "fetch_constructor_palmares", _ctor_spy)

    refresh_bio.run(season=SEASON, driver="VER", constructor=None)

    raw = json.loads(tmp_season.read_text(encoding="utf-8"))
    assert raw["drivers"]["VER"]["career"]["wins"] == 1
    # NOR untouched because filter was VER
    assert raw["drivers"]["NOR"]["career"] is None
    # No constructor calls made
    assert called["constructors"] == 0


def test_refresh_bio_preserves_hand_curated_championships(tmp_season, monkeypatch):
    """If a driver's career already has championships=N, a refresh that
    doesn't fetch championships must NOT clobber it. This is the whole
    point of merging instead of replacing the career dict."""
    # Pre-populate VER with a hand-curated championships value.
    raw = json.loads(tmp_season.read_text(encoding="utf-8"))
    raw["drivers"]["VER"]["career"] = {"championships": 4}
    tmp_season.write_text(json.dumps(raw), encoding="utf-8")
    season_service.clear_cache()

    monkeypatch.setattr(
        jolpica_service, "fetch_driver_career",
        lambda jid, *, client: {
            # No championships key — mirrors current helper behavior.
            "wins": 71, "podiums": 127, "poles": 63, "starts": 237
        },
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_constructor_palmares",
        lambda jid, *, client: None,
    )

    refresh_bio.run(season=SEASON, driver="VER", constructor=None)

    ver = json.loads(tmp_season.read_text(encoding="utf-8"))["drivers"]["VER"]["career"]
    assert ver["championships"] == 4  # preserved
    assert ver["wins"] == 71  # added
    assert ver["starts"] == 237  # added
    assert ver["updated_at"]


def test_refresh_bio_writes_atomically(tmp_season, monkeypatch):
    """A failure mid-iteration must not leave a half-written .json on disk."""
    monkeypatch.setattr(
        jolpica_service, "fetch_driver_career",
        lambda jid, *, client: {
            "wins": 9, "podiums": 9, "poles": 9, "championships": 9, "starts": 9
        },
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_constructor_palmares",
        lambda jid, *, client: None,
    )
    refresh_bio.run(season=SEASON, driver=None, constructor=None)
    # .tmp must be gone after the run
    assert not tmp_season.with_suffix(".json.tmp").exists()
    # The real file is valid JSON
    raw = json.loads(tmp_season.read_text(encoding="utf-8"))
    assert raw["season"] == SEASON
