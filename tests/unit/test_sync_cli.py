"""`f1 sync` CLI — Jolpica patched, real CSV/JSON read/write, no network."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import app as cli_app
from app.config import Settings
from app.pipeline import rebuild
from app.services import jolpica_service, season_service

runner = CliRunner()

SEASON = 8888

SEED_JSON = {
    "season": SEASON,
    "teams": {
        "Red Bull": {"color": "#3671C6"},
        "McLaren": {"color": "#FF8000"},
    },
    "drivers": {
        "VER": {
            "name": "Max Verstappen", "team": "Red Bull", "number": 1, "flag": "🇳🇱",
            "jolpica_id": "max_verstappen", "career": None,
        },
        "NOR": {
            "name": "Lando Norris", "team": "McLaren", "number": 4, "flag": "🇬🇧",
            "jolpica_id": "norris", "career": None,
        },
    },
    "constructors": {
        "Red Bull": {"jolpica_id": "red_bull", "palmares": None},
        "McLaren": {"jolpica_id": "mclaren", "palmares": None},
    },
    "rounds": {"1": "AUS"},
    "sprint_rounds": [],
}

SEED_CSV = "Driver,1\nVER,25\nNOR,18\n"


def _schedule(*, future_only: bool = False) -> list[dict]:
    rounds = [
        {"round": 1, "name": "Australian GP", "circuit_id": "albert_park",
         "country": "Australia", "date": "2020-03-08", "has_sprint": False},
        {"round": 2, "name": "Chinese GP", "circuit_id": "shanghai",
         "country": "China", "date": "2020-03-15", "has_sprint": True},
        {"round": 3, "name": "Japanese GP", "circuit_id": "suzuka",
         "country": "Japan", "date": "2999-01-01", "has_sprint": False},
    ]
    return rounds[2:] if future_only else rounds


@pytest.fixture
def sync_env(tmp_path: Path, monkeypatch):
    data = tmp_path / "data"
    seasons = data / "seasons"
    instance = tmp_path / "instance"
    for d in (data, seasons, instance):
        d.mkdir(parents=True, exist_ok=True)

    json_path = seasons / f"{SEASON}.json"
    json_path.write_text(json.dumps(SEED_JSON, indent=4), encoding="utf-8")
    csv_path = data / f"championships_{SEASON}.csv"
    csv_path.write_text(SEED_CSV, encoding="utf-8")

    settings = Settings(
        database_path=instance / "sync.db",
        data_folder=data,
        seasons_folder=seasons,
        default_season=SEASON,
    )
    for name in (
        "app.config",
        "app.cli.sync",
        "app.cli.refresh_bio",
        "app.services.season_service",
        "app.data.session",
        "app.cache.service",
    ):
        mod = __import__(name, fromlist=["get_settings"])
        if hasattr(mod, "get_settings"):
            monkeypatch.setattr(mod, "get_settings", lambda s=settings: s)
    season_service.clear_cache()

    # Network defaults: schedule with one fetchable round; no bio data.
    monkeypatch.setattr(
        jolpica_service, "fetch_schedule", lambda season, *, client=None: _schedule()
    )
    monkeypatch.setattr(
        jolpica_service,
        "fetch_weekend",
        lambda season, rnd, *, client=None: (
            ({"VER": 25, "NOR": 18}, {"VER": 8, "NOR": 7})
            if rnd == 2
            else (_ for _ in ()).throw(jolpica_service.RoundNotFoundError("no data"))
        ),
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_driver_career", lambda jid, *, client: None
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_constructor_palmares", lambda jid, *, client: None
    )

    rebuild_calls: list[int] = []
    monkeypatch.setattr(
        rebuild,
        "rebuild_season",
        lambda settings, season, *, echo=print: rebuild_calls.append(season) or (3, 3),
    )

    class Env:
        pass

    env = Env()
    env.settings = settings
    env.json_path = json_path
    env.csv_path = csv_path
    env.rebuild_calls = rebuild_calls
    env.monkeypatch = monkeypatch
    yield env
    season_service.clear_cache()


def test_sync_fetches_missing_round_and_updates_files(sync_env):
    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])
    assert result.exit_code == 0, result.output

    csv = sync_env.csv_path.read_text(encoding="utf-8")
    assert csv.splitlines()[0] == "Driver,1,2,2s"
    raw = json.loads(sync_env.json_path.read_text(encoding="utf-8"))
    assert raw["rounds"] == {"1": "AUS", "2": "CHN", "3": "JPN"}
    assert raw["sprint_rounds"] == [2]
    # New CSV data -> full rebuild triggered.
    assert sync_env.rebuild_calls == [SEASON]


def test_sync_no_reprocess_skips_rebuild(sync_env):
    result = runner.invoke(
        cli_app, ["sync", "--season", str(SEASON), "--no-bio", "--no-reprocess"]
    )
    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == []


def test_sync_skips_round_when_results_not_posted(sync_env):
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_weekend",
        lambda season, rnd, *, client=None: (_ for _ in ()).throw(
            jolpica_service.RoundNotFoundError("results not up yet")
        ),
    )
    before_csv = sync_env.csv_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])
    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_bytes() == before_csv
    assert "no results yet" in result.output.lower()
    assert sync_env.rebuild_calls == []


def test_sync_dry_run_writes_nothing(sync_env):
    before_csv = sync_env.csv_path.read_bytes()
    before_json = sync_env.json_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_bytes() == before_csv
    assert sync_env.json_path.read_bytes() == before_json
    assert sync_env.rebuild_calls == []
    assert "round 2" in result.output.lower()


def test_sync_noop_when_up_to_date(sync_env):
    # Calendar already matches, no missing rounds, nothing to do.
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: [
            {"round": 1, "name": "Australian GP", "circuit_id": "albert_park",
             "country": "Australia", "date": "2020-03-08", "has_sprint": False},
        ],
    )
    # Make the CSV's round the only one.
    before_csv = sync_env.csv_path.read_bytes()
    before_json = sync_env.json_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])
    assert result.exit_code == 0, result.output
    assert "up to date" in result.output.lower()
    assert sync_env.csv_path.read_bytes() == before_csv
    assert sync_env.json_path.read_bytes() == before_json
    assert sync_env.rebuild_calls == []


def test_sync_adds_stub_for_unknown_driver(sync_env):
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_weekend",
        lambda season, rnd, *, client=None: (
            ({"VER": 25, "ZZZ": 15}, {}) if rnd == 2
            else (_ for _ in ()).throw(jolpica_service.RoundNotFoundError("x"))
        ),
    )
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_season_drivers",
        lambda season, *, client=None: {
            "ZZZ": {
                "jolpica_id": "zed", "name": "Zed Zedson", "number": 99,
                "birthdate": "2000-01-01", "nationality": "Dutch",
            }
        },
    )
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_driver_constructor",
        lambda season, driver_id, *, client=None: "red_bull",
    )
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_driver_first_season",
        lambda driver_id, *, client=None: 2020,
    )

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])
    assert result.exit_code == 0, result.output

    raw = json.loads(sync_env.json_path.read_text(encoding="utf-8"))
    zed = raw["drivers"]["ZZZ"]
    assert zed["name"] == "Zed Zedson"
    assert zed["team"] == "Red Bull"  # resolved via constructors jolpica_id
    assert zed["flag"] == "🇳🇱"
    assert zed["number"] == 99
    assert zed["debut_year"] == 2020
    assert zed["jolpica_id"] == "zed"


def test_sync_bio_runs_automatically_when_new_rounds_land(sync_env):
    career_calls: list[str] = []

    def _career(jid, *, client):
        career_calls.append(jid)
        return None

    sync_env.monkeypatch.setattr(jolpica_service, "fetch_driver_career", _career)

    runner.invoke(cli_app, ["sync", "--season", str(SEASON)])
    assert career_calls  # bio refresh ran because round 2 landed


def test_sync_bio_skipped_when_no_new_rounds(sync_env):
    career_calls: list[str] = []

    def _career(jid, *, client):
        career_calls.append(jid)
        return None

    sync_env.monkeypatch.setattr(jolpica_service, "fetch_driver_career", _career)
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_weekend",
        lambda season, rnd, *, client=None: (_ for _ in ()).throw(
            jolpica_service.RoundNotFoundError("x")
        ),
    )

    runner.invoke(cli_app, ["sync", "--season", str(SEASON)])
    assert career_calls == []


def test_sync_forced_bio_runs_even_without_new_rounds(sync_env):
    career_calls: list[str] = []

    def _career(jid, *, client):
        career_calls.append(jid)
        return None

    sync_env.monkeypatch.setattr(jolpica_service, "fetch_driver_career", _career)
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_weekend",
        lambda season, rnd, *, client=None: (_ for _ in ()).throw(
            jolpica_service.RoundNotFoundError("x")
        ),
    )

    runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--bio"])
    assert career_calls


def test_sync_exits_cleanly_when_jolpica_lacks_season(sync_env):
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: (_ for _ in ()).throw(
            jolpica_service.RoundNotFoundError("no schedule")
        ),
    )
    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON)])
    assert result.exit_code == 0
    assert "no schedule" in result.output.lower()


def test_sync_errors_when_season_json_missing(sync_env):
    result = runner.invoke(cli_app, ["sync", "--season", "1234"])
    assert result.exit_code == 1
    assert "new-season" in result.output  # points at the scaffolding command
