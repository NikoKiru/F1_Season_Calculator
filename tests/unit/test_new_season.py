"""`f1 new-season` CLI — scaffolds a season JSON from the API, carrying over
curated fields (colors, principals, championships) from the previous season."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import app as cli_app
from app.config import Settings
from app.services import jolpica_service, season_service

runner = CliRunner()

PREV = 8888
TARGET = 8889

PREV_JSON = {
    "season": PREV,
    "teams": {"Red Bull": {"color": "#3671C6"}},
    "drivers": {
        "VER": {
            "name": "Max Verstappen", "team": "Red Bull", "number": 1, "flag": "🇳🇱",
            "nationality": "Dutch", "birthdate": "1997-09-30", "debut_year": 2015,
            "jolpica_id": "max_verstappen",
            "career": {"wins": 71, "championships": 4, "updated_at": "then"},
        },
    },
    "constructors": {
        "Red Bull": {
            "country": "Austria", "founded": 2005, "principal": "Laurent Mekies",
            "power_unit": "Honda RBPT", "chassis": "RB22", "jolpica_id": "red_bull",
            "palmares": {"championships": 6, "wins": 130, "updated_at": "then"},
        },
    },
    "rounds": {"1": "AUS"},
    "sprint_rounds": [],
}


@pytest.fixture
def scaffold_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    seasons = data / "seasons"
    seasons.mkdir(parents=True)
    (seasons / f"{PREV}.json").write_text(json.dumps(PREV_JSON), encoding="utf-8")

    settings = Settings(
        database_path=tmp_path / "instance" / "x.db",
        data_folder=data,
        seasons_folder=seasons,
        default_season=PREV,
    )
    for name in ("app.config", "app.cli.new_season", "app.services.season_service"):
        mod = __import__(name, fromlist=["get_settings"])
        if hasattr(mod, "get_settings"):
            monkeypatch.setattr(mod, "get_settings", lambda s=settings: s)
    season_service.clear_cache()

    monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: [
            {"round": 1, "name": "Australian GP", "circuit_id": "albert_park",
             "country": "Australia", "date": "2027-03-07", "has_sprint": False},
            {"round": 2, "name": "Chinese GP", "circuit_id": "shanghai",
             "country": "China", "date": "2027-03-14", "has_sprint": True},
        ],
    )
    monkeypatch.setattr(
        jolpica_service,
        "fetch_season_constructors",
        lambda season, *, client=None: [
            {"jolpica_id": "red_bull", "name": "Red Bull", "nationality": "Austrian"},
            {"jolpica_id": "audi", "name": "Audi", "nationality": "German"},
        ],
    )
    monkeypatch.setattr(
        jolpica_service,
        "fetch_season_drivers",
        lambda season, *, client=None: {
            "VER": {
                "jolpica_id": "max_verstappen", "name": "Max Verstappen",
                "number": 3, "birthdate": "1997-09-30", "nationality": "Dutch",
            },
            "NEW": {
                "jolpica_id": "newbie", "name": "Nina Newbie",
                "number": 77, "birthdate": "2008-05-05", "nationality": "German",
            },
        },
    )
    monkeypatch.setattr(
        jolpica_service,
        "fetch_driver_constructor",
        lambda season, driver_id, *, client=None: (
            "red_bull" if driver_id == "max_verstappen" else "audi"
        ),
    )
    monkeypatch.setattr(
        jolpica_service,
        "fetch_driver_first_season",
        lambda driver_id, *, client=None: 2015 if driver_id == "max_verstappen" else TARGET,
    )

    class Env:
        pass

    env = Env()
    env.seasons = seasons
    env.target_path = seasons / f"{TARGET}.json"
    env.monkeypatch = monkeypatch
    yield env
    season_service.clear_cache()


def test_new_season_scaffolds_from_api_with_carry_over(scaffold_env):
    result = runner.invoke(
        cli_app,
        ["new-season", "--season", str(TARGET), "--from-season", str(PREV)],
    )
    assert result.exit_code == 0, result.output
    raw = json.loads(scaffold_env.target_path.read_text(encoding="utf-8"))

    assert raw["season"] == TARGET
    assert raw["rounds"] == {"1": "AUS", "2": "CHN"}
    assert raw["sprint_rounds"] == [2]

    # Carried team keeps its curated color and metadata.
    assert raw["teams"]["Red Bull"]["color"] == "#3671C6"
    rb = raw["constructors"]["Red Bull"]
    assert rb["principal"] == "Laurent Mekies"
    assert rb["palmares"]["championships"] == 6
    # New team gets a placeholder color.
    assert raw["teams"]["Audi"]["color"] == "#888888"
    assert raw["constructors"]["Audi"]["jolpica_id"] == "audi"

    # Carried driver: career (and title count) survives, number updates from API.
    ver = raw["drivers"]["VER"]
    assert ver["team"] == "Red Bull"
    assert ver["career"]["championships"] == 4
    assert ver["number"] == 3
    assert ver["debut_year"] == 2015
    # New driver scaffolded from API.
    new = raw["drivers"]["NEW"]
    assert new["team"] == "Audi"
    assert new["flag"] == "🇩🇪"
    assert new["debut_year"] == TARGET
    assert new["career"] is None


def test_new_season_refuses_to_overwrite_without_force(scaffold_env):
    scaffold_env.target_path.write_text("{}", encoding="utf-8")
    result = runner.invoke(cli_app, ["new-season", "--season", str(TARGET)])
    assert result.exit_code == 1
    assert scaffold_env.target_path.read_text(encoding="utf-8") == "{}"

    result = runner.invoke(cli_app, ["new-season", "--season", str(TARGET), "--force"])
    assert result.exit_code == 0, result.output
    assert json.loads(scaffold_env.target_path.read_text(encoding="utf-8"))["season"] == TARGET


def test_new_season_exits_when_schedule_unpublished(scaffold_env):
    scaffold_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: (_ for _ in ()).throw(
            jolpica_service.RoundNotFoundError("nope")
        ),
    )
    result = runner.invoke(cli_app, ["new-season", "--season", str(TARGET)])
    assert result.exit_code == 1
    assert not scaffold_env.target_path.exists()
