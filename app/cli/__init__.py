"""Typer CLI entry point — `f1 <command>` after install."""
from __future__ import annotations

import typer

from app.cli import add_race, compute_stats, fetch_race, process_data, setup


app = typer.Typer(
    name="f1",
    help="F1 Season Calculator — data pipeline and maintenance commands.",
    no_args_is_help=True,
    add_completion=False,
)

app.command(name="setup", help="Create data dirs and a sample CSV.")(setup.run)
app.command(name="process-data", help="Generate every championship combination for a season.")(
    process_data.run
)
app.command(name="compute-stats", help="Pre-compute driver stats + win-probability cache.")(
    compute_stats.run
)
app.command(name="add-race", help="Add a single race to a season and re-process.")(add_race.run)
app.command(name="fetch-race", help="Fetch a weekend's race + sprint results from Jolpica.")(
    fetch_race.run
)


def main() -> None:  # entry point declared in pyproject.toml
    app()
