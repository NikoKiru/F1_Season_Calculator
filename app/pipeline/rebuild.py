"""Full-season rebuild: WDC combinations + stats, then WCC + stats.

One shared entry point for every code path that changes a season's CSV
(`add-race`, `fetch-race`, `sync`) so the chain can't drift between commands.

A finished rebuild stamps the hash of the CSV it consumed. The stamp goes in
last and `clear_season` removes it, so `is_current` only holds for a complete
build of the CSV as it stands now.
"""
from __future__ import annotations

import hashlib
import sqlite3
import time
from collections.abc import Callable
from pathlib import Path

from app.config import Settings
from app.pipeline import (
    constructor_builder,
    constructor_stats_compute,
    constructor_writer,
    csv_loader,
    init_db,
    stats_compute,
    writer,
)


def _csv_sha256(csv_path: Path) -> str:
    return hashlib.sha256(csv_path.read_bytes()).hexdigest()


def is_current(settings: Settings, season: int) -> bool:
    """True when the database holds a finished build of the season CSV as it is now."""
    if not settings.database_path.exists():
        return False
    conn = sqlite3.connect(settings.database_path)
    try:
        row = conn.execute(
            "SELECT csv_sha256 FROM season_builds WHERE season = ?", (season,)
        ).fetchone()
    except sqlite3.OperationalError:  # database predates build tracking
        return False
    finally:
        conn.close()
    csv_path = settings.data_folder / f"championships_{season}.csv"
    return row is not None and row[0] == _csv_sha256(csv_path)


def rebuild_season(
    settings: Settings, season: int, *, echo: Callable[[str], None] = print
) -> tuple[int, int]:
    """Regenerate every championship + stats table for a season.

    Returns (wdc_rows, wcc_rows) inserted. Ensures the schema exists first so
    a fresh clone can sync without running `f1 setup`.
    """
    csv_path = settings.data_folder / f"championships_{season}.csv"
    init_db.ensure_schema(settings.database_path)

    echo("Reprocessing season (this regenerates every combination)…")
    csv_sha256 = _csv_sha256(csv_path)
    loaded = csv_loader.load(csv_path)
    writer.clear_season(settings.database_path, season)
    start = time.time()
    inserted = writer.process_season(settings.database_path, loaded, season=season)
    echo(f"[OK] {inserted:,} championships ({time.time() - start:.1f}s)")

    stats_compute.compute(settings.database_path, season, on_progress=echo)

    echo("Reprocessing constructors (WCC)…")
    built = constructor_builder.build(loaded, season)
    constructor_writer.clear_season(settings.database_path, season)
    inserted_wcc = constructor_writer.process_season(
        settings.database_path, built, season=season
    )
    echo(f"[OK] {inserted_wcc:,} constructor championships")
    constructor_stats_compute.compute(settings.database_path, season, on_progress=echo)

    conn = sqlite3.connect(settings.database_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO season_builds (season, csv_sha256) VALUES (?, ?)",
            (season, csv_sha256),
        )
        conn.commit()
    finally:
        conn.close()
    echo(f"[OK] season {season} ready")
    return inserted, inserted_wcc
