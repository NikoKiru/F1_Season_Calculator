"""Derive a constructor score matrix from a driver `LoadedSeason`.

For each weekend column, sum the (race + sprint) points of every driver on
each team into a single per-constructor score. The output shape mirrors
`LoadedSeason` so the existing combinator + writer pipeline can ingest it.

Team membership is read from `data/seasons/{year}.json::drivers[code].team`.
Drivers whose team is missing from the season metadata are logged and
skipped.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import numpy as np

from app.pipeline.csv_loader import LoadedSeason
from app.services import season_service

log = logging.getLogger("f1.pipeline.constructor_builder")


@dataclass(frozen=True)
class LoadedConstructorSeason:
    constructors: np.ndarray  # shape (T,), team names
    round_numbers: np.ndarray  # shape (W,), same weekend axis as LoadedSeason
    combined: np.ndarray  # shape (T, W), race + sprint summed per weekend


def build(loaded: LoadedSeason, season: int) -> LoadedConstructorSeason:
    sd = season_service.get_season_data(season)

    # TODO: per-round team — if a driver moves teams mid-season, weekly sums
    # should follow that movement. Today we trust the static `info.team`.
    teams_in_order: list[str] = []
    indices_by_team: dict[str, list[int]] = {}
    for i, code in enumerate(loaded.drivers.tolist()):
        info = sd.drivers.get(code)
        if info is None:
            log.warning(
                "constructor_builder: driver %s not in season %d metadata — skipping",
                code, season,
            )
            continue
        team = info.team
        if team not in indices_by_team:
            indices_by_team[team] = []
            teams_in_order.append(team)
        indices_by_team[team].append(i)

    combined_driver = loaded.combined  # (D, W)
    weeks = combined_driver.shape[1]

    if not teams_in_order:
        return LoadedConstructorSeason(
            constructors=np.empty(0, dtype=object),
            round_numbers=loaded.round_numbers.copy(),
            combined=np.zeros((0, weeks), dtype=int),
        )

    stacked = np.vstack(
        [combined_driver[indices_by_team[team], :].sum(axis=0) for team in teams_in_order]
    )
    return LoadedConstructorSeason(
        constructors=np.asarray(teams_in_order, dtype=object),
        round_numbers=loaded.round_numbers.copy(),
        combined=stacked.astype(int),
    )
