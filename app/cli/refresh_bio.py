"""`f1 refresh-bio` — top up career totals + palmarès from Jolpica/Ergast.

Reads data/seasons/{year}.json, hits Jolpica for each driver + constructor
with a `jolpica_id`, writes career/palmarès counts (with an updated_at
timestamp) back into the same JSON. Atomic write via .tmp + replace().

Records without a jolpica_id are skipped with a warning. Network failures
leave the existing data intact so a flaky Jolpica never wipes your numbers.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import httpx
import typer

from app.config import get_settings
from app.services import jolpica_service, season_service


def run(
    season: int = typer.Option(..., "--season", "-s", help="Season year."),
    driver: str = typer.Option(
        None,
        "--driver",
        "-d",
        help="Only refresh this driver code (e.g. VER). Skips constructors.",
    ),
    constructor: str = typer.Option(
        None,
        "--constructor",
        "-c",
        help="Only refresh this constructor name. Skips drivers.",
    ),
) -> None:
    settings = get_settings()
    path = settings.seasons_folder / f"{season}.json"
    if not path.exists():
        typer.echo(f"[ERR] {path} not found", err=True)
        raise typer.Exit(code=1)

    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    now_iso = datetime.now(timezone.utc).isoformat()
    drivers_done = 0
    drivers_skipped = 0
    teams_done = 0
    teams_skipped = 0

    with httpx.Client(timeout=15.0) as client:
        if constructor is None:
            for code, drv in raw.get("drivers", {}).items():
                if driver and code != driver.upper():
                    continue
                jid = drv.get("jolpica_id")
                if not jid:
                    typer.echo(f"[skip] {code}: no jolpica_id")
                    drivers_skipped += 1
                    continue
                typer.echo(f"  -> {code} ({jid})")
                career = jolpica_service.fetch_driver_career(jid, client=client)
                if career is None:
                    typer.echo(f"[warn] {code}: Jolpica had no data for '{jid}'")
                    drivers_skipped += 1
                    continue
                # Merge into existing career so hand-curated fields
                # (e.g. championships) survive a refresh.
                existing = drv.get("career") or {}
                drv["career"] = {**existing, **career, "updated_at": now_iso}
                drivers_done += 1

        if driver is None:
            for name, ctor in raw.get("constructors", {}).items():
                if constructor and name != constructor:
                    continue
                jid = ctor.get("jolpica_id")
                if not jid:
                    typer.echo(f"[skip] {name}: no jolpica_id")
                    teams_skipped += 1
                    continue
                typer.echo(f"  -> {name} ({jid})")
                pal = jolpica_service.fetch_constructor_palmares(jid, client=client)
                if pal is None:
                    typer.echo(f"[warn] {name}: Jolpica had no data for '{jid}'")
                    teams_skipped += 1
                    continue
                existing = ctor.get("palmares") or {}
                ctor["palmares"] = {**existing, **pal, "updated_at": now_iso}
                teams_done += 1

    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(raw, f, indent=4, ensure_ascii=False)
    tmp.replace(path)
    season_service.clear_cache()

    typer.echo(
        f"[OK] drivers: {drivers_done} refreshed, {drivers_skipped} skipped; "
        f"constructors: {teams_done} refreshed, {teams_skipped} skipped."
    )
