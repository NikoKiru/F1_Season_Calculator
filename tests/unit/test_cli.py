"""Thin smoke tests for the Typer CLI — make sure every command wires up."""
from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from app import config as config_mod
from app.cli import app as cli_app
from app.services import season_service


runner = CliRunner()


@pytest.fixture
def cli_settings(tmp_path, monkeypatch):
    data = tmp_path / "data"
    seasons = data / "seasons"
    instance = tmp_path / "instance"
    for d in (data, seasons, instance):
        d.mkdir(parents=True, exist_ok=True)

    test_settings = config_mod.Settings(
        database_path=instance / "cli.db",
        data_folder=data,
        seasons_folder=seasons,
        default_season=2099,
    )
    for name in (
        "app.config",
        "app.cli.setup",
        "app.cli.process_data",
        "app.cli.compute_stats",
        "app.cli.add_race",
        "app.cli.fetch_race",
        "app.services.season_service",
        "app.data.session",
        "app.cache.service",
    ):
        mod = __import__(name, fromlist=["get_settings"])
        if hasattr(mod, "get_settings"):
            monkeypatch.setattr(mod, "get_settings", lambda s=test_settings: s)
    season_service.clear_cache()
    yield test_settings
    season_service.clear_cache()


def test_help_lists_all_commands():
    result = runner.invoke(cli_app, ["--help"])
    assert result.exit_code == 0
    for cmd in ("setup", "process-data", "compute-stats", "add-race", "fetch-race"):
        assert cmd in result.stdout


def test_setup_creates_sample_and_schema(cli_settings):
    result = runner.invoke(cli_app, ["setup"])
    assert result.exit_code == 0, result.stdout
    assert (cli_settings.data_folder / "championships_sample.csv").exists()
    assert cli_settings.database_path.exists()


def test_process_data_end_to_end(cli_settings):
    # Write a small CSV + season JSON and run the pipeline via CLI.
    csv = cli_settings.data_folder / "championships_2099.csv"
    csv.write_text("Driver,1,2,3\nVER,25,18,25\nNOR,18,25,18\nLEC,15,15,15\n")
    (cli_settings.seasons_folder / "2099.json").write_text(
        '{"teams":{"Red Bull":{"color":"#000"}},'
        '"drivers":{'
        '"VER":{"name":"Max","team":"Red Bull","number":1,"flag":""},'
        '"NOR":{"name":"Lando","team":"Red Bull","number":2,"flag":""},'
        '"LEC":{"name":"Charles","team":"Red Bull","number":3,"flag":""}},'
        '"rounds":{"1":"r1","2":"r2","3":"r3"}}'
    )

    setup_r = runner.invoke(cli_app, ["setup"])
    assert setup_r.exit_code == 0

    proc_r = runner.invoke(cli_app, ["process-data", "--season", "2099"])
    assert proc_r.exit_code == 0, proc_r.stdout

    stats_r = runner.invoke(cli_app, ["compute-stats", "--season", "2099"])
    assert stats_r.exit_code == 0, stats_r.stdout

    # Validate DB has 7 championships for 3 races (2^3 - 1).
    from sqlalchemy import create_engine, text

    eng = create_engine(f"sqlite:///{cli_settings.database_path}")
    with eng.connect() as c:
        count = c.execute(
            text("SELECT COUNT(*) FROM championship_results WHERE season=:s"), {"s": 2099}
        ).scalar()
    eng.dispose()
    assert count == 7


def test_add_race_appends_and_reprocesses(cli_settings):
    csv = cli_settings.data_folder / "championships_2099.csv"
    csv.write_text("Driver,1,2\nVER,25,18\nNOR,18,25\nLEC,15,15\n")
    (cli_settings.seasons_folder / "2099.json").write_text(
        '{"teams":{"Red Bull":{"color":"#000"}},'
        '"drivers":{'
        '"VER":{"name":"Max","team":"Red Bull","number":1,"flag":""},'
        '"NOR":{"name":"Lando","team":"Red Bull","number":2,"flag":""},'
        '"LEC":{"name":"Charles","team":"Red Bull","number":3,"flag":""}},'
        '"rounds":{"1":"r1","2":"r2","3":"r3"}}'
    )

    assert runner.invoke(cli_app, ["setup"]).exit_code == 0
    assert runner.invoke(cli_app, ["process-data", "--season", "2099"]).exit_code == 0

    add = runner.invoke(
        cli_app,
        ["add-race", "--season", "2099", "--race", "3", "--results", "VER:25,NOR:18,LEC:15"],
    )
    assert add.exit_code == 0, add.stdout

    content = csv.read_text()
    header = content.splitlines()[0]
    assert header.split(",")[-1] == "3"


def test_fetch_race_splices_jolpica_results(cli_settings, monkeypatch):
    csv = cli_settings.data_folder / "championships_2099.csv"
    csv.write_text("Driver,1\nVER,25\nNOR,18\nLEC,15\n")
    (cli_settings.seasons_folder / "2099.json").write_text(
        '{"teams":{"Red Bull":{"color":"#000"}},'
        '"drivers":{'
        '"VER":{"name":"Max","team":"Red Bull","number":1,"flag":""},'
        '"NOR":{"name":"Lando","team":"Red Bull","number":2,"flag":""},'
        '"LEC":{"name":"Charles","team":"Red Bull","number":3,"flag":""}},'
        '"rounds":{"1":"r1","2":"r2"},'
        '"sprint_rounds":[2]}'
    )
    assert runner.invoke(cli_app, ["setup"]).exit_code == 0
    assert runner.invoke(cli_app, ["process-data", "--season", "2099"]).exit_code == 0

    from app.cli import fetch_race as fetch_race_mod

    def fake_fetch_weekend(season, round_number, *, client=None):
        assert season == 2099 and round_number == 2
        return ({"VER": 18, "NOR": 25, "LEC": 15}, {"VER": 8, "NOR": 7, "LEC": 6})

    monkeypatch.setattr(
        fetch_race_mod.jolpica_service, "fetch_weekend", fake_fetch_weekend
    )

    result = runner.invoke(
        cli_app, ["fetch-race", "--season", "2099", "--round", "2"]
    )
    assert result.exit_code == 0, result.stdout

    content = csv.read_text()
    header = content.splitlines()[0].split(",")
    # Expect race column "2" and sprint column "2s" now present
    assert "2" in header
    assert "2s" in header


def test_fetch_race_round_not_found(cli_settings, monkeypatch):
    csv = cli_settings.data_folder / "championships_2099.csv"
    csv.write_text("Driver,1\nVER,25\n")
    (cli_settings.seasons_folder / "2099.json").write_text(
        '{"teams":{},"drivers":{"VER":{"name":"Max","team":"","number":1,"flag":""}},'
        '"rounds":{"1":"r1"}}'
    )
    assert runner.invoke(cli_app, ["setup"]).exit_code == 0

    from app.cli import fetch_race as fetch_race_mod
    from app.services import jolpica_service

    def fake_fetch_weekend(season, round_number, *, client=None):
        raise jolpica_service.RoundNotFoundError("no such round")

    monkeypatch.setattr(
        fetch_race_mod.jolpica_service, "fetch_weekend", fake_fetch_weekend
    )

    result = runner.invoke(
        cli_app, ["fetch-race", "--season", "2099", "--round", "99", "--no-reprocess"]
    )
    assert result.exit_code == 1
