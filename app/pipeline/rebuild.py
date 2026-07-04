"""Full-season rebuild: WDC combinations + stats, then WCC + stats.

One shared entry point for every code path that changes a season's CSV
(`add-race`, `fetch-race`, `sync`) so the chain can't drift between commands.
"""
from __future__ import annotations

import time
from collections.abc import Callable

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
    echo(f"[OK] season {season} ready")
    return inserted, inserted_wcc
