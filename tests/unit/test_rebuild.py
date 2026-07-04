"""rebuild_season — the shared WDC + WCC + stats chain."""
from __future__ import annotations

import sqlite3

import pytest

from app.config import Settings
from app.pipeline import rebuild
from app.services import season_service

CSV = "Driver,1,2,2s\nVER,25,18,8\nNOR,18,25,7\n"

SEASON = 7777

JSON = (
    '{"season": 7777,'
    '"teams": {"Red Bull": {"color": "#111"}, "McLaren": {"color": "#222"}},'
    '"drivers": {'
    '"VER": {"name": "Max", "team": "Red Bull", "number": 1, "flag": ""},'
    '"NOR": {"name": "Lando", "team": "McLaren", "number": 4, "flag": ""}},'
    '"rounds": {"1": "AUS", "2": "CHN"}, "sprint_rounds": [2]}'
)


@pytest.fixture
def settings(tmp_path, monkeypatch) -> Settings:
    data = tmp_path / "data"
    seasons = data / "seasons"
    seasons.mkdir(parents=True)
    (data / f"championships_{SEASON}.csv").write_text(CSV, encoding="utf-8")
    (seasons / f"{SEASON}.json").write_text(JSON, encoding="utf-8")

    s = Settings(
        database_path=tmp_path / "instance" / "t.db",
        data_folder=data,
        seasons_folder=seasons,
        default_season=SEASON,
    )
    for name in ("app.config", "app.services.season_service", "app.data.session"):
        mod = __import__(name, fromlist=["get_settings"])
        if hasattr(mod, "get_settings"):
            monkeypatch.setattr(mod, "get_settings", lambda s=s: s)
    season_service.clear_cache()
    yield s
    season_service.clear_cache()


def test_rebuild_season_fills_wdc_and_wcc_tables(settings):
    logs: list[str] = []
    inserted_wdc, inserted_wcc = rebuild.rebuild_season(
        settings, SEASON, echo=logs.append
    )

    # 2 rounds -> 3 non-empty subsets each for WDC and WCC.
    assert inserted_wdc == 3
    assert inserted_wcc == 3

    con = sqlite3.connect(settings.database_path)
    try:
        n_champs = con.execute(
            "SELECT COUNT(*) FROM championship_results WHERE season = ?", (SEASON,)
        ).fetchone()[0]
        n_wcc = con.execute(
            "SELECT COUNT(*) FROM constructor_championship_results WHERE season = ?",
            (SEASON,),
        ).fetchone()[0]
    finally:
        con.close()
    assert n_champs == 3
    assert n_wcc == 3
    assert logs  # progress was reported


def test_rebuild_season_is_rerunnable(settings):
    """Second run replaces rows instead of duplicating them."""
    rebuild.rebuild_season(settings, SEASON, echo=lambda _: None)
    wdc, wcc = rebuild.rebuild_season(settings, SEASON, echo=lambda _: None)
    assert (wdc, wcc) == (3, 3)
