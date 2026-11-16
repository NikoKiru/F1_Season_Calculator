"""Pre-compute the drivers' statistics tables for a season.

The work is in `season_stats`, shared with `constructor_stats_compute`. This
side also mines the notable scenarios.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from app.pipeline import season_stats
from app.pipeline.tables import DRIVERS

# The cache tables this pass writes to, declared here as well as in schema.py
# so that `f1 compute-stats` works on a database that predates them without
# running the whole schema.
_CACHE_DDL = (
    """
    CREATE TABLE IF NOT EXISTS driver_head_to_head (
        season INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        opponent TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (season, driver_code, opponent)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_h2h_season_driver ON driver_head_to_head (season, driver_code)",
    """
    CREATE TABLE IF NOT EXISTS driver_position_distribution (
        season INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        position INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (season, driver_code, position)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS notable_scenarios (
        season INTEGER NOT NULL,
        category TEXT NOT NULL,
        championship_id INTEGER,
        metric_value INTEGER,
        detail TEXT,
        PRIMARY KEY (season, category)
    )
    """,
)


def compute(
    db_path: Path,
    season: int,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Populate driver_statistics, win_probability_cache, driver_head_to_head,
    driver_position_distribution and notable_scenarios for `season`.

    Returns a small summary dict: {'drivers': n, 'probability_rows': m, ...}.
    """
    return season_stats.compute(
        db_path,
        DRIVERS,
        season,
        noun="drivers",
        ddl=_CACHE_DDL,
        notable=True,
        on_progress=on_progress,
    )
