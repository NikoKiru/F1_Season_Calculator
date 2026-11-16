"""Pre-compute the constructors' statistics tables for a season.

The work is in `season_stats`, shared with `stats_compute`.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.pipeline import season_stats
from app.pipeline.tables import CONSTRUCTORS

# Declared here as well as in schema.py, for the reason given in stats_compute.
_CACHE_DDL = (
    """
    CREATE TABLE IF NOT EXISTS constructor_head_to_head (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        opponent TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (season, constructor_name, opponent)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_constructor_h2h_season "
    "ON constructor_head_to_head (season, constructor_name)",
    """
    CREATE TABLE IF NOT EXISTS constructor_position_distribution (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        position INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (season, constructor_name, position)
    )
    """,
)


def compute(
    db_path: Path,
    season: int,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Populate constructor_statistics, constructor_win_probability_cache,
    constructor_head_to_head and constructor_position_distribution."""
    return season_stats.compute(
        db_path,
        CONSTRUCTORS,
        season,
        noun="constructors",
        ddl=_CACHE_DDL,
        on_progress=on_progress,
    )
