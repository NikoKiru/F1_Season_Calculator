"""Unit tests for the constructor score-matrix builder."""
from __future__ import annotations

import numpy as np
import pytest

from app.domain.driver import DriverInfo
from app.domain.season import SeasonData
from app.pipeline import constructor_builder
from app.pipeline.csv_loader import LoadedSeason


def _fake_season(drivers_by_team: dict[str, list[str]]) -> SeasonData:
    teams = {team: "#000000" for team in drivers_by_team}
    drivers = {}
    for team, codes in drivers_by_team.items():
        for code in codes:
            drivers[code] = DriverInfo(
                name=code, team=team, number=0, flag="X", color="#000000"
            )
    return SeasonData(
        season=9999,
        teams=teams,
        drivers=drivers,
        driver_names={c: c for c in drivers},
        round_names={},
    )


def test_build_sums_drivers_by_team(monkeypatch):
    # 4 drivers across 2 teams over 3 weekends; sprint at round 2 only.
    drivers = np.array(["AAA", "BBB", "CCC", "DDD"], dtype=object)
    race = np.array(
        [
            [10, 0, 5],
            [5, 10, 0],
            [0, 5, 10],
            [10, 10, 10],
        ]
    )
    sprint = np.array(
        [
            [0, 2, 0],
            [0, 1, 0],
            [0, 3, 0],
            [0, 0, 0],
        ]
    )
    loaded = LoadedSeason(
        drivers=drivers,
        round_numbers=np.array([1, 2, 3]),
        race_scores=race,
        sprint_scores=sprint,
    )
    fake = _fake_season({"TeamX": ["AAA", "BBB"], "TeamY": ["CCC", "DDD"]})
    monkeypatch.setattr(
        constructor_builder.season_service, "get_season_data", lambda _s: fake
    )

    built = constructor_builder.build(loaded, 9999)

    assert built.constructors.tolist() == ["TeamX", "TeamY"]
    # TeamX = AAA + BBB; TeamY = CCC + DDD; sprint counts toward weekend total.
    assert built.combined.tolist() == [
        [15, 13, 5],
        [10, 18, 20],
    ]
    assert built.round_numbers.tolist() == [1, 2, 3]


def test_build_skips_driver_missing_from_season_metadata(monkeypatch, caplog):
    drivers = np.array(["AAA", "ZZZ"], dtype=object)
    race = np.array([[10, 5], [3, 4]])
    sprint = np.zeros_like(race)
    loaded = LoadedSeason(
        drivers=drivers,
        round_numbers=np.array([1, 2]),
        race_scores=race,
        sprint_scores=sprint,
    )
    fake = _fake_season({"TeamX": ["AAA"]})
    monkeypatch.setattr(
        constructor_builder.season_service, "get_season_data", lambda _s: fake
    )

    with caplog.at_level("WARNING", logger="f1.pipeline.constructor_builder"):
        built = constructor_builder.build(loaded, 9999)

    assert built.constructors.tolist() == ["TeamX"]
    assert built.combined.tolist() == [[10, 5]]
    assert any("ZZZ" in rec.message for rec in caplog.records)


def test_build_empty_when_no_drivers_match(monkeypatch):
    loaded = LoadedSeason(
        drivers=np.array(["XYZ"], dtype=object),
        round_numbers=np.array([1, 2]),
        race_scores=np.array([[1, 2]]),
        sprint_scores=np.zeros((1, 2), dtype=int),
    )
    fake = _fake_season({})
    monkeypatch.setattr(
        constructor_builder.season_service, "get_season_data", lambda _s: fake
    )

    built = constructor_builder.build(loaded, 9999)
    assert built.constructors.shape == (0,)
    assert built.combined.shape == (0, 2)


def test_build_preserves_first_seen_team_order(monkeypatch):
    # First-seen order: order in `loaded.drivers` controls constructor ordering.
    drivers = np.array(["AAA", "BBB", "CCC", "DDD"], dtype=object)
    race = np.array([[1], [2], [3], [4]])
    sprint = np.zeros_like(race)
    loaded = LoadedSeason(
        drivers=drivers,
        round_numbers=np.array([1]),
        race_scores=race,
        sprint_scores=sprint,
    )
    fake = _fake_season({"Y": ["BBB", "DDD"], "X": ["AAA", "CCC"]})
    monkeypatch.setattr(
        constructor_builder.season_service, "get_season_data", lambda _s: fake
    )

    built = constructor_builder.build(loaded, 9999)
    # First-seen team in driver-order: AAA→X first, then BBB→Y.
    assert built.constructors.tolist() == ["X", "Y"]


@pytest.fixture(autouse=True)
def _clear_season_cache():
    from app.services import season_service
    season_service.clear_cache()
    yield
    season_service.clear_cache()
