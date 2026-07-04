"""`f1 add-race` — splice a new race (and optional sprint) into a season's CSV."""
from __future__ import annotations

import typer

from app.config import get_settings
from app.pipeline import race_csv, rebuild


def run(
    season: int = typer.Option(..., "--season", "-s"),
    race: int = typer.Option(..., "--race", "-r", help="Round number for the new race."),
    results: str = typer.Option(
        ...,
        "--results",
        help='Race results. Comma-separated "DRIVER:POINTS" (e.g. "VER:25,NOR:18,LEC:15").',
    ),
    sprint: str = typer.Option(
        "",
        "--sprint",
        help='Optional sprint results for the same weekend (e.g. "VER:8,NOR:7,LEC:6").',
    ),
) -> None:
    settings = get_settings()
    csv_path = settings.data_folder / f"championships_{season}.csv"

    race_parsed = race_csv.parse_results(results)
    sprint_parsed = race_csv.parse_results(sprint) if sprint else None

    drivers, race_data, sprint_data = race_csv.load(csv_path)
    drivers = race_csv.apply_race(
        race_data, sprint_data, drivers, race, race_parsed, sprint_parsed
    )
    race_csv.save(csv_path, drivers, race_data, sprint_data)
    typer.echo(
        f"[OK] wrote {csv_path.name} "
        f"(round {race}{' + sprint' if sprint_parsed else ''})"
    )

    rebuild.rebuild_season(settings, season, echo=typer.echo)
