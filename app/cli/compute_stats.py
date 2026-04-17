"""`f1 compute-stats` — pre-compute driver_statistics + win_probability_cache."""
from __future__ import annotations

import sqlite3
import time

import typer

from app.config import get_settings
from app.pipeline import stats_compute


def run(
    season: int = typer.Option(
        None, "--season", "-s", help="Season year. Omit to compute for every season."
    ),
) -> None:
    settings = get_settings()
    db_path = settings.database_path

    if season is not None:
        seasons = [season]
    else:
        conn = sqlite3.connect(db_path)
        try:
            seasons = [
                row[0]
                for row in conn.execute(
                    "SELECT DISTINCT season FROM championship_results ORDER BY season"
                )
            ]
        finally:
            conn.close()
        if not seasons:
            typer.echo("[ERROR] no championship data — run `f1 process-data` first", err=True)
            raise typer.Exit(code=1)

    for s in seasons:
        start = time.time()
        summary = stats_compute.compute(db_path, s, on_progress=typer.echo)
        typer.echo(f"[OK] season {s}: {summary} ({time.time() - start:.1f}s)")
