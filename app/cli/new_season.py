"""`f1 new-season` — scaffold data/seasons/{YYYY}.json from the Jolpica API.

Pulls the calendar, sprint flags, constructor list, and driver roster for the
new year. Hand-curated facts the API can't provide — team colors, principals,
power units, chassis, championship titles — carry over from the previous
season's JSON (matched by jolpica_id); brand-new entries get placeholders and
a printed curation checklist.

Run once the FIA calendar lands in Jolpica, then `f1 sync` keeps the season
current all year.
"""
from __future__ import annotations

import time

import httpx
import typer

from app.cli.refresh_bio import save_season_json
from app.config import get_settings
from app.services import circuit_codes, flags, jolpica_service, season_service


def _load_previous(seasons_folder, from_season: int) -> dict:
    path = seasons_folder / f"{from_season}.json"
    if not path.exists():
        return {}
    import json

    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run(
    season: int = typer.Option(..., "--season", "-s", help="Season year to scaffold."),
    from_season: int = typer.Option(
        None,
        "--from-season",
        help="Season JSON to carry curated fields from. Default: season - 1.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite an existing seasons/{YYYY}.json."
    ),
) -> None:
    settings = get_settings()
    target = settings.seasons_folder / f"{season}.json"
    if target.exists() and not force:
        typer.echo(f"[ERR] {target} already exists — pass --force to overwrite.", err=True)
        raise typer.Exit(code=1)

    prev = _load_previous(settings.seasons_folder, from_season or season - 1)
    prev_teams = prev.get("teams", {})
    prev_ctors = prev.get("constructors", {})
    prev_drivers = prev.get("drivers", {})
    prev_career_by_jid = {
        d.get("jolpica_id"): d for d in prev_drivers.values() if d.get("jolpica_id")
    }

    curation: list[str] = []

    with httpx.Client(timeout=15.0) as client:
        typer.echo(f"Fetching {season} calendar…")
        try:
            schedule = jolpica_service.fetch_schedule(season, client=client)
        except jolpica_service.RoundNotFoundError:
            typer.echo(
                f"[ERR] Jolpica has no {season} calendar yet — try again once the "
                "FIA schedule is published.",
                err=True,
            )
            raise typer.Exit(code=1) from None
        except jolpica_service.JolpicaError as e:
            typer.echo(f"[ERR] {e}", err=True)
            raise typer.Exit(code=1) from e

        rounds: dict[str, str] = {}
        for entry in schedule:
            label = circuit_codes.lookup(entry["circuit_id"])
            if label is None:
                label = circuit_codes.fallback(entry["circuit_id"])
                curation.append(
                    f"round {entry['round']}: unknown circuit '{entry['circuit_id']}' "
                    f"labeled {label} — rename if wrong"
                )
            rounds[str(entry["round"])] = label
        sprint_rounds = sorted(e["round"] for e in schedule if e["has_sprint"])

        typer.echo("Fetching constructors…")
        time.sleep(jolpica_service.THROTTLE_SECONDS)
        api_ctors = jolpica_service.fetch_season_constructors(season, client=client)
        teams: dict[str, dict] = {}
        constructors: dict[str, dict] = {}
        name_by_ctor_id: dict[str, str] = {}
        for ctor in api_ctors:
            jid = ctor["jolpica_id"]
            prev_name = next(
                (n for n, c in prev_ctors.items() if c.get("jolpica_id") == jid), None
            )
            name = prev_name or ctor["name"]
            name_by_ctor_id[jid] = name
            teams[name] = dict(prev_teams.get(name) or {"color": "#888888"})
            if prev_name:
                entry = dict(prev_ctors[prev_name])
            else:
                entry = {
                    "country": None,
                    "founded": season,
                    "principal": None,
                    "power_unit": None,
                    "chassis": None,
                    "palmares": None,
                }
                curation.append(f"team '{name}': set color, principal, power_unit, chassis")
            entry["jolpica_id"] = jid
            constructors[name] = entry
            if prev_name:
                curation.append(
                    f"team '{name}': verify principal/power_unit/chassis for {season}"
                )

        typer.echo("Fetching driver roster…")
        time.sleep(jolpica_service.THROTTLE_SECONDS)
        api_drivers = jolpica_service.fetch_season_drivers(season, client=client)
        drivers: dict[str, dict] = {}
        for code, info in sorted(api_drivers.items()):
            jid = info["jolpica_id"]
            time.sleep(jolpica_service.THROTTLE_SECONDS)
            ctor_id = jolpica_service.fetch_driver_constructor(season, jid, client=client)
            team = name_by_ctor_id.get(ctor_id or "", "")
            if not team:
                curation.append(f"driver {code}: could not resolve team — fill in manually")
            carried = prev_career_by_jid.get(jid, {})
            debut = carried.get("debut_year")
            if debut is None:
                time.sleep(jolpica_service.THROTTLE_SECONDS)
                debut = jolpica_service.fetch_driver_first_season(jid, client=client)
            drivers[code] = {
                "name": info["name"] or carried.get("name", ""),
                "team": team,
                "number": info["number"] or carried.get("number", 0),
                "flag": carried.get("flag") or flags.flag_for(info["nationality"]),
                "nationality": info["nationality"] or carried.get("nationality"),
                "birthdate": info["birthdate"] or carried.get("birthdate"),
                "debut_year": debut,
                "jolpica_id": jid,
                "career": carried.get("career"),
            }
            typer.echo(f"  {code}: {drivers[code]['name']} ({team or '???'})")

    raw = {
        "season": season,
        "teams": teams,
        "drivers": drivers,
        "constructors": constructors,
        "rounds": rounds,
        "sprint_rounds": sprint_rounds,
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    save_season_json(target, raw)
    season_service.clear_cache()
    typer.echo(f"[OK] wrote {target}")

    if curation:
        typer.echo("\nHand-curation checklist:")
        for item in curation:
            typer.echo(f"  - {item}")
    typer.echo(
        f"\nNext: `f1 sync --season {season}` once results start landing "
        f"(it also fills career stats via --bio)."
    )
