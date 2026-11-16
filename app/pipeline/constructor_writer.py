"""Write the constructors' championship (WCC) scenarios of a season.

The work is in `season_writer`, shared with `writer`.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.pipeline import season_writer
from app.pipeline.constructor_builder import LoadedConstructorSeason
from app.pipeline.tables import CONSTRUCTORS


def process_season(
    db_path: Path,
    built: LoadedConstructorSeason,
    season: int,
    batch_size: int = 100_000,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    return season_writer.write_season(
        db_path,
        CONSTRUCTORS,
        built.constructors,
        built.combined,
        built.countback,
        built.round_numbers,
        season,
        batch_size=batch_size,
        on_progress=on_progress,
    )


def clear_season(db_path: Path, season: int) -> None:
    """Remove every constructor-side row for a season. Used before a reprocess."""
    season_writer.clear_season(db_path, CONSTRUCTORS, season)
