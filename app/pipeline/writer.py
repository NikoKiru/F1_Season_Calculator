"""Write the drivers' championship (WDC) scenarios of a season.

The work is in `season_writer`, shared with `constructor_writer`.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.pipeline import season_writer
from app.pipeline.csv_loader import LoadedSeason
from app.pipeline.tables import DRIVERS


def process_season(
    db_path: Path,
    loaded: LoadedSeason,
    season: int,
    batch_size: int = 100_000,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Generate + insert every weekend combination for one season. Returns row count."""
    return season_writer.write_season(
        db_path,
        DRIVERS,
        loaded.drivers,
        loaded.combined,
        loaded.countback,
        loaded.round_numbers,
        season,
        batch_size=batch_size,
        on_progress=on_progress,
    )


def clear_season(db_path: Path, season: int) -> None:
    """Remove every driver-side row for a season. Used before a reprocess."""
    season_writer.clear_season(db_path, DRIVERS, season)
