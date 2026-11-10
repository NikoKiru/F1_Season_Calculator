"""`f1 sync` CLI — Jolpica patched, real CSV/JSON read/write, no network."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from app.cli import app as cli_app
from app.config import Settings
from app.pipeline import rebuild, writer
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

    # The seed CSV starts out built, so only what a test does can make it stale.
    rebuild.rebuild_season(settings, SEASON, echo=lambda _: None)

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
    # The season-wide results the recheck compares the CSV with. Empty means
    # the API has nothing to say, so a test opts in with _api_results().
    monkeypatch.setattr(
        jolpica_service, "fetch_season_results", lambda season, *, client=None: {}
    )
    monkeypatch.setattr(
        jolpica_service, "fetch_season_sprints", lambda season, *, client=None: {}
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


def _nothing_to_fetch(sync_env) -> None:
    """The API calendar is exactly the round the seed CSV already holds."""
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: [
            {"round": 1, "name": "Australian GP", "circuit_id": "albert_park",
             "country": "Australia", "date": "2020-03-08", "has_sprint": False},
        ],
    )


def test_sync_noop_when_up_to_date(sync_env):
    _nothing_to_fetch(sync_env)
    before_csv = sync_env.csv_path.read_bytes()
    before_json = sync_env.json_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])
    assert result.exit_code == 0, result.output
    assert "up to date" in result.output.lower()
    assert sync_env.csv_path.read_bytes() == before_csv
    assert sync_env.json_path.read_bytes() == before_json
    assert sync_env.rebuild_calls == []


def test_sync_rebuilds_when_csv_changed_without_a_fetch(sync_env):
    # What `git pull` does: the CSV moves on, the API has nothing new to offer.
    _nothing_to_fetch(sync_env)
    sync_env.csv_path.write_text("Driver,1\nVER,18\nNOR,25\n", encoding="utf-8")

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == [SEASON]
    assert "up to date" not in result.output.lower()


def test_sync_finishes_a_rebuild_that_never_completed(sync_env):
    _nothing_to_fetch(sync_env)
    writer.clear_season(sync_env.settings.database_path, SEASON)

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == [SEASON]


def test_sync_no_reprocess_leaves_a_stale_database_alone(sync_env):
    _nothing_to_fetch(sync_env)
    sync_env.csv_path.write_text("Driver,1\nVER,18\nNOR,25\n", encoding="utf-8")

    result = runner.invoke(
        cli_app, ["sync", "--season", str(SEASON), "--no-bio", "--no-reprocess"]
    )

    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == []


def test_sync_dry_run_reports_a_stale_database_without_rebuilding(sync_env):
    _nothing_to_fetch(sync_env)
    sync_env.csv_path.write_text("Driver,1\nVER,18\nNOR,25\n", encoding="utf-8")

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == []
    assert "would rebuild" in result.output.lower()
    assert "up to date" not in result.output.lower()


def test_sync_before_the_first_race_has_nothing_to_rebuild(sync_env):
    # A new season: schedule published, no CSV yet.
    sync_env.csv_path.unlink()
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: _schedule(future_only=True),
    )

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.rebuild_calls == []


def test_sync_interrupted_by_bio_refresh_is_redone_in_full_next_run(sync_env):
    def lost_connection(jid, *, client):
        raise RuntimeError("connection lost")

    sync_env.monkeypatch.setattr(jolpica_service, "fetch_driver_career", lost_connection)

    interrupted = runner.invoke(cli_app, ["sync", "--season", str(SEASON)])

    assert interrupted.exit_code != 0
    assert sync_env.csv_path.read_text(encoding="utf-8") == SEED_CSV
    assert sync_env.rebuild_calls == []

    career_calls: list[str] = []
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_driver_career",
        lambda jid, *, client: career_calls.append(jid),
    )

    resumed = runner.invoke(cli_app, ["sync", "--season", str(SEASON)])

    assert resumed.exit_code == 0, resumed.output
    assert career_calls  # bios weren't lost with the first attempt
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines()[0] == "Driver,1,2,2s"
    assert sync_env.rebuild_calls == [SEASON]


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


# --- Git state --------------------------------------------------------------


def _git(repo: Path, *args: str, check: bool = True) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=Test", "-c", "user.email=test@example.com", *args],
        check=check,
        capture_output=True,
    )


def _commit_all(repo: Path, message: str) -> None:
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)


def _start_conflicted_merge(repo: Path) -> None:
    notes = repo / "notes.txt"
    _git(repo, "init", "-b", "main")
    notes.write_text("base\n", encoding="utf-8")
    _commit_all(repo, "base")
    _git(repo, "checkout", "-b", "other")
    notes.write_text("theirs\n", encoding="utf-8")
    _commit_all(repo, "theirs")
    _git(repo, "checkout", "main")
    notes.write_text("ours\n", encoding="utf-8")
    _commit_all(repo, "ours")
    _git(repo, "merge", "other", check=False)


def _fail_if_called(*_args, **_kwargs):
    raise AssertionError("sync must not reach the API")


def test_sync_refuses_to_run_during_an_unfinished_merge(sync_env):
    _start_conflicted_merge(sync_env.settings.data_folder)
    sync_env.monkeypatch.setattr(jolpica_service, "fetch_schedule", _fail_if_called)
    before = sync_env.csv_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 1
    assert "unfinished git merge" in result.output
    assert sync_env.csv_path.read_bytes() == before


def test_dry_run_only_warns_about_an_unfinished_merge(sync_env):
    _start_conflicted_merge(sync_env.settings.data_folder)

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "[warn]" in result.output
    assert "unfinished git merge" in result.output


def test_sync_warns_when_the_checkout_is_behind_upstream(sync_env, tmp_path: Path):
    data = sync_env.settings.data_folder
    origin = tmp_path / "origin.git"
    origin.mkdir()
    _git(origin, "init", "--bare", "-b", "main")
    _git(data, "init", "-b", "main")
    _commit_all(data, "base")
    _git(data, "remote", "add", "origin", str(origin))
    _git(data, "push", "-u", "origin", "main")

    other = tmp_path / "other"
    subprocess.run(["git", "clone", str(origin), str(other)], check=True, capture_output=True)
    (other / "bot.txt").write_text("from the bot\n", encoding="utf-8")
    _commit_all(other, "data: auto-sync")
    _git(other, "push")

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert "1 commit behind" in result.output
    assert "git pull" in result.output


# --- revised results ------------------------------------------------------
# The seed CSV has round 1 as VER 25, NOR 18. Jolpica corrects results after
# the fact, and the CSV has to follow or every scenario is built on old points.


def _api_results(sync_env, races: dict, sprints: dict | None = None) -> None:
    sync_env.monkeypatch.setattr(
        jolpica_service, "fetch_season_results", lambda season, *, client=None: races
    )
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_season_sprints",
        lambda season, *, client=None: sprints or {},
    )


def test_sync_corrects_a_revised_result(sync_env):
    _nothing_to_fetch(sync_env)
    _api_results(sync_env, {1: {"VER": 18, "NOR": 25}})

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines() == [
        "Driver,1", "VER,18", "NOR,25",
    ]
    assert "round 1" in result.output
    assert "VER 25 -> 18" in result.output
    assert sync_env.rebuild_calls == [SEASON]
    assert "up to date" not in result.output.lower()


def test_sync_leaves_matching_results_alone(sync_env):
    _nothing_to_fetch(sync_env)
    _api_results(sync_env, {1: {"VER": 25, "NOR": 18}})
    before = sync_env.csv_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_bytes() == before
    assert sync_env.rebuild_calls == []
    assert "up to date" in result.output.lower()


def test_sync_zeroes_a_driver_who_lost_the_result(sync_env):
    _nothing_to_fetch(sync_env)
    _api_results(sync_env, {1: {"VER": 25}})

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines() == [
        "Driver,1", "VER,25", "NOR,0",
    ]


def test_sync_adds_a_sprint_that_was_missing_at_first_fetch(sync_env):
    _nothing_to_fetch(sync_env)
    _api_results(
        sync_env, {1: {"VER": 25, "NOR": 18}}, sprints={1: {"VER": 8, "NOR": 7}}
    )

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines() == [
        "Driver,1,1s", "VER,25,8", "NOR,18,7",
    ]
    assert "round 1 sprint" in result.output


def test_sync_dry_run_reports_revisions_without_writing(sync_env):
    _nothing_to_fetch(sync_env)
    _api_results(sync_env, {1: {"VER": 18, "NOR": 25}})
    before = sync_env.csv_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--dry-run"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_bytes() == before
    assert "would correct round 1" in result.output
    assert "up to date" not in result.output.lower()
    assert sync_env.rebuild_calls == []


def test_sync_does_not_recheck_a_round_that_became_another_race(sync_env):
    # The schedule now has Shanghai at round 1, the season file Australia.
    sync_env.monkeypatch.setattr(
        jolpica_service,
        "fetch_schedule",
        lambda season, *, client=None: [
            {"round": 1, "name": "Chinese GP", "circuit_id": "shanghai",
             "country": "China", "date": "2020-03-08", "has_sprint": False},
        ],
    )
    _api_results(sync_env, {1: {"VER": 18, "NOR": 25}})
    before = sync_env.csv_path.read_bytes()

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_bytes() == before
    assert "not rechecked" in result.output
    assert sync_env.rebuild_calls == []


def test_sync_carries_on_when_the_recheck_cannot_reach_the_api(sync_env):
    def unreachable(season, *, client=None):
        raise jolpica_service.JolpicaError("rate limited")

    sync_env.monkeypatch.setattr(jolpica_service, "fetch_season_results", unreachable)

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert "could not recheck" in result.output
    # The new round still lands.
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines()[0] == "Driver,1,2,2s"


def test_sync_does_not_recheck_the_rounds_it_just_fetched(sync_env):
    # Round 2 arrives in this run; the season feed can still lag behind it.
    _api_results(sync_env, {1: {"VER": 25, "NOR": 18}, 2: {"VER": 1, "NOR": 2}})

    result = runner.invoke(cli_app, ["sync", "--season", str(SEASON), "--no-bio"])

    assert result.exit_code == 0, result.output
    assert sync_env.csv_path.read_text(encoding="utf-8").splitlines() == [
        "Driver,1,2,2s", "VER,25,25,8", "NOR,18,18,7",
    ]
