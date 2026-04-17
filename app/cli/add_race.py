"""`f1 add-race` — splice a new race into a season's CSV and re-process."""
from __future__ import annotations

import time

import typer

from app.config import get_settings
from app.pipeline import csv_loader, race_csv, stats_compute, writer


def run(
    season: int = typer.Option(..., "--season", "-s"),
    race: int = typer.Option(..., "--race", "-r", help="Round number for the new race."),
    results: str = typer.Option(
        ...,
        "--results",
        help='Comma-separated "DRIVER:POINTS" pairs (e.g. "VER:25,NOR:18,LEC:15").',
    ),
) -> None:
    settings = get_settings()
    csv_path = settings.data_folder / f"championships_{season}.csv"

    parsed = race_csv.parse_results(results)
    drivers, data = race_csv.load(csv_path)

    drivers = race_csv.apply_race(data, drivers, race, parsed)
    max_round = max(max(rounds) for rounds in data.values())
    race_csv.save(csv_path, drivers, data, max_round)
    typer.echo(f"[OK] wrote {csv_path.name} with {len(drivers)} drivers × {max_round} rounds")

    typer.echo("Reprocessing season (this regenerates every combination)…")
    drivers_np, scores_np = csv_loader.load(csv_path)
    writer.clear_season(settings.database_path, season)
    start = time.time()
    inserted = writer.process_season(
        settings.database_path, drivers_np, scores_np, season=season
    )
    typer.echo(f"[OK] {inserted:,} championships ({time.time() - start:.1f}s)")

    stats_compute.compute(settings.database_path, season, on_progress=typer.echo)
    typer.echo(f"[OK] season {season} ready")
