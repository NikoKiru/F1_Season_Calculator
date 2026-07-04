"""`f1 fetch-race` — pull a weekend's race + sprint results from Jolpica.

Thin wrapper over `add-race`: the only difference is where results come from.
Results go straight into the season CSV; the season is then reprocessed.
"""
from __future__ import annotations

import typer

from app.config import get_settings
from app.pipeline import race_csv, rebuild
from app.services import jolpica_service, season_service


def run(
    season: int = typer.Option(..., "--season", "-s"),
    round_number: int = typer.Option(..., "--round", "-r", help="Round number to fetch."),
    no_reprocess: bool = typer.Option(
        False,
        "--no-reprocess",
        help="Only write the CSV; skip re-generating combinations + stats.",
    ),
) -> None:
    settings = get_settings()
    csv_path = settings.data_folder / f"championships_{season}.csv"

    # Honor season metadata for sprint-ness, but also trust Jolpica if it has data.
    try:
        sd = season_service.get_season_data(season)
        expected_sprint = sd.is_sprint(round_number)
    except (FileNotFoundError, KeyError):
        expected_sprint = False

    typer.echo(f"Fetching {season} round {round_number} from Jolpica…")
    try:
        race, sprint = jolpica_service.fetch_weekend(season, round_number)
    except jolpica_service.RoundNotFoundError as e:
        typer.echo(f"[ERR] {e}", err=True)
        raise typer.Exit(code=1) from e

    typer.echo(
        f"[OK] race: {len(race)} drivers; sprint: {len(sprint)} drivers"
        + (" (expected sprint weekend)" if expected_sprint else "")
    )

    drivers, race_data, sprint_data = race_csv.load(csv_path)
    drivers = race_csv.apply_race(
        race_data,
        sprint_data,
        drivers,
        round_number,
        race,
        sprint or None,
    )
    race_csv.save(csv_path, drivers, race_data, sprint_data)
    typer.echo(f"[OK] wrote {csv_path.name}")

    if no_reprocess:
        typer.echo("Skipping reprocess (--no-reprocess).")
        return

    rebuild.rebuild_season(settings, season, echo=typer.echo)
