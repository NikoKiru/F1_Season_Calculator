"""The table names of the two championships.

The drivers' (WDC) and constructors' (WCC) sides store the same shapes under
different names. The writer and the stats pass are written once against this
description and run for either side.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SeasonTables:
    results: str  # one row per scenario
    positions: str  # one row per entry per scenario
    entry: str  # the column naming a driver or a constructor
    statistics: str
    win_probability: str
    head_to_head: str
    position_distribution: str
    # Tables only this side has that hold season rows, cleared with the rest.
    extra: tuple[str, ...] = ()

    @property
    def derived(self) -> tuple[str, ...]:
        """Every table a rebuild of one season rewrites."""
        return (
            self.positions,
            self.results,
            self.statistics,
            self.win_probability,
            self.head_to_head,
            self.position_distribution,
            *self.extra,
        )


DRIVERS = SeasonTables(
    results="championship_results",
    positions="position_results",
    entry="driver_code",
    statistics="driver_statistics",
    win_probability="win_probability_cache",
    head_to_head="driver_head_to_head",
    position_distribution="driver_position_distribution",
    extra=("notable_scenarios",),
)

CONSTRUCTORS = SeasonTables(
    results="constructor_championship_results",
    positions="constructor_position_results",
    entry="constructor_name",
    statistics="constructor_statistics",
    win_probability="constructor_win_probability_cache",
    head_to_head="constructor_head_to_head",
    position_distribution="constructor_position_distribution",
)
