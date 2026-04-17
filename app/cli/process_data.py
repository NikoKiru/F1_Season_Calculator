"""`f1 process-data` — generate all championships for a season."""
from __future__ import annotations

import time

import typer

from app.config import get_settings
from app.pipeline import csv_loader, init_db, writer


def run(
    season: int = typer.Option(..., "--season", "-s", help="Season year to process."),
    batch_size: int = typer.Option(100_000, "--batch-size", help="Rows per insert batch."),
    clear: bool = typer.Option(
        True,
        "--clear/--keep",
        help="Delete existing rows for this season before inserting. Default: clear.",
    ),
) -> None:
    settings = get_settings()
    init_db.ensure_schema(settings.database_path)

    csv_path = csv_loader.resolve_csv(settings.data_folder, season)
    typer.echo(f"CSV: {csv_path}")

    drivers, scores = csv_loader.load(csv_path)
    typer.echo(f"drivers={len(drivers)} rounds={scores.shape[1]}")

    if clear:
        writer.clear_season(settings.database_path, season)
        typer.echo(f"cleared existing rows for season {season}")

    start = time.time()

    def log(done: int, total: int) -> None:
        pct = (done / total) * 100 if total else 0
        typer.echo(f"  {done:,}/{total:,} ({pct:.1f}%) — {time.time() - start:.1f}s")

    inserted = writer.process_season(
        settings.database_path,
        drivers,
        scores,
        season=season,
        batch_size=batch_size,
        on_progress=log,
    )
    typer.echo(f"[OK] {inserted:,} championships inserted in {time.time() - start:.1f}s")
