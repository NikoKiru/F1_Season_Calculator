"""`f1 setup` — first-time project initialization."""
from __future__ import annotations

from pathlib import Path

import typer

from app.config import get_settings
from app.pipeline import init_db


_SAMPLE_CSV = """Driver,1,2,3
VER,25,18,25
NOR,18,25,18
LEC,15,15,15
"""


def run(
    clear: bool = typer.Option(False, "--clear", help="Delete existing DB before init."),
) -> None:
    settings = get_settings()
    data_folder = settings.data_folder
    data_folder.mkdir(parents=True, exist_ok=True)
    typer.echo(f"[OK] data folder: {data_folder}")

    sample = data_folder / "championships_sample.csv"
    if not sample.exists():
        sample.write_text(_SAMPLE_CSV, encoding="utf-8")
        typer.echo(f"[OK] wrote sample CSV: {sample.name}")

    if clear:
        init_db.reset(settings.database_path)
        typer.echo(f"[OK] reset DB: {settings.database_path}")
    else:
        init_db.ensure_schema(settings.database_path)
        typer.echo(f"[OK] schema ready: {settings.database_path}")
