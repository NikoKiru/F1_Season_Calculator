"""`f1 sync` — bring a season fully up to date from the Jolpica-F1 API.

One idempotent command that replaces the manual fetch-race/refresh-bio dance:

1. Calendar: merge the API schedule into data/seasons/{Y}.json (labels for
   raced rounds are frozen; future rounds follow the schedule, including
   cancellations and sprint flags).
2. Results: fetch every completed round missing from the season CSV and
   splice it in. Rounds whose results aren't posted yet are skipped politely.
3. Roster: drivers who appear in results but not in the season JSON get a
   stub scaffolded from the API (substitutes, mid-season rookies).
4. Bios: career/palmarès counts refresh automatically when new rounds land
   (`--bio` forces, `--no-bio` skips). Timestamps only move on real changes.
5. Rebuild: championships + stats are regenerated once when new results
   arrived, unless --no-reprocess (used by CI, which only syncs data files).

A run with nothing to do makes one API call and touches no files, so it is
safe on a timer, in CI, or behind a UI button.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import httpx
import typer

from app.cli import refresh_bio
from app.config import get_settings
from app.pipeline import race_csv, rebuild
from app.services import flags, jolpica_service, season_service, sync_service


def _load_raced(csv_path) -> tuple[list[str], dict, dict, set[int], set[int]]:
    drivers, race_data, sprint_data = race_csv.load(csv_path)
    raced_rounds = {r for per_driver in race_data.values() for r in per_driver}
    raced_sprints = {r for per_driver in sprint_data.values() for r in per_driver}
    return drivers, race_data, sprint_data, raced_rounds, raced_sprints


def _team_name_for(raw: dict, constructor_id: str | None) -> str | None:
    if not constructor_id:
        return None
    for name, ctor in raw.get("constructors", {}).items():
        if ctor.get("jolpica_id") == constructor_id:
            return name
    return None


def _add_driver_stubs(
    raw: dict,
    gaps: list[str],
    season: int,
    *,
    client: httpx.Client,
    echo,
) -> bool:
    """Scaffold JSON entries for drivers that raced but aren't in the roster."""
    try:
        season_drivers = jolpica_service.fetch_season_drivers(season, client=client)
    except jolpica_service.JolpicaError as e:
        echo(f"[warn] could not fetch season roster: {e}")
        return False

    changed = False
    for code in gaps:
        info = season_drivers.get(code)
        if info is None:
            echo(f"[warn] {code}: raced but unknown to Jolpica — add to JSON manually")
            continue
        jid = info["jolpica_id"]
        constructor_id = jolpica_service.fetch_driver_constructor(
            season, jid, client=client
        )
        team = _team_name_for(raw, constructor_id)
        if team is None and constructor_id:
            # Brand-new team mid-season: scaffold it too.
            api_ctors = jolpica_service.fetch_season_constructors(season, client=client)
            api_name = next(
                (c["name"] for c in api_ctors if c["jolpica_id"] == constructor_id),
                constructor_id,
            )
            raw.setdefault("teams", {})[api_name] = {"color": "#888888"}
            raw.setdefault("constructors", {})[api_name] = {
                "jolpica_id": constructor_id,
                "palmares": None,
            }
            echo(f"[warn] new team '{api_name}' scaffolded — set its color in the JSON")
            team = api_name
        raw.setdefault("drivers", {})[code] = {
            "name": info["name"],
            "team": team or "",
            "number": info["number"],
            "flag": flags.flag_for(info["nationality"]),
            "nationality": info["nationality"],
            "birthdate": info["birthdate"],
            "debut_year": jolpica_service.fetch_driver_first_season(jid, client=client),
            "jolpica_id": jid,
            "career": None,
        }
        echo(f"[OK] added roster stub for {code} ({info['name']}, {team or 'team unknown'})")
        changed = True
    return changed


def run(
    season: int = typer.Option(
        None, "--season", "-s", help="Defaults to the newest data/seasons/*.json."
    ),
    reprocess: bool = typer.Option(
        True,
        "--reprocess/--no-reprocess",
        help="Rebuild championships + stats when new results land.",
    ),
    bio: bool = typer.Option(
        None,
        "--bio/--no-bio",
        help="Refresh career totals. Default: only when new rounds land.",
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would change without writing anything."
    ),
) -> None:
    settings = get_settings()
    if season is None:
        season = season_service.default_season()

    json_path = settings.seasons_folder / f"{season}.json"
    if not json_path.exists():
        typer.echo(
            f"[ERR] {json_path} not found — scaffold it with "
            f"`f1 new-season --season {season}` first.",
            err=True,
        )
        raise typer.Exit(code=1)
    with json_path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    csv_path = settings.data_folder / f"championships_{season}.csv"

    with httpx.Client(timeout=15.0) as client:
        typer.echo(f"Fetching {season} schedule from Jolpica…")
        try:
            schedule = jolpica_service.fetch_schedule(season, client=client)
        except jolpica_service.RoundNotFoundError:
            typer.echo(f"Jolpica has no schedule for {season} yet — nothing to sync.")
            return
        except jolpica_service.JolpicaError as e:
            typer.echo(f"[ERR] {e}", err=True)
            raise typer.Exit(code=1) from e

        drivers, race_data, sprint_data, raced_rounds, raced_sprints = _load_raced(
            csv_path
        )
        today = datetime.now(timezone.utc).date()
        missing = sync_service.plan_missing_rounds(schedule, raced_rounds, today=today)

        if dry_run:
            _, changes = sync_service.merge_schedule(
                raw, schedule, raced_rounds=raced_rounds, raced_sprints=raced_sprints
            )
            for line in changes:
                typer.echo(f"  calendar: {line}")
            for rnd in missing:
                typer.echo(f"  results: would fetch round {rnd}")
            if not changes and not missing:
                typer.echo("Season is up to date.")
            typer.echo("(dry run — nothing written)")
            return

        # --- Results ------------------------------------------------------
        fetched: list[int] = []
        for i, rnd in enumerate(missing):
            if i:
                time.sleep(jolpica_service.THROTTLE_SECONDS)
            try:
                race, sprint = jolpica_service.fetch_weekend(season, rnd, client=client)
            except jolpica_service.RoundNotFoundError:
                typer.echo(f"  round {rnd}: no results yet — skipping")
                continue
            except jolpica_service.JolpicaError as e:
                typer.echo(f"[warn] round {rnd}: {e} — skipping")
                continue
            drivers = race_csv.apply_race(
                race_data, sprint_data, drivers, rnd, race, sprint or None
            )
            fetched.append(rnd)
            typer.echo(
                f"  round {rnd}: {len(race)} race results"
                + (f", {len(sprint)} sprint results" if sprint else "")
            )
        if fetched:
            race_csv.save(csv_path, drivers, race_data, sprint_data)
            typer.echo(f"[OK] wrote {csv_path.name} (rounds {fetched})")
            raced_rounds |= set(fetched)
            raced_sprints |= {
                r for per_driver in sprint_data.values() for r in per_driver
            }

        # --- Calendar metadata ---------------------------------------------
        raw, cal_changes = sync_service.merge_schedule(
            raw, schedule, raced_rounds=raced_rounds, raced_sprints=raced_sprints
        )
        for line in cal_changes:
            typer.echo(f"  calendar: {line}")

        # --- Roster stubs ---------------------------------------------------
        gaps = sync_service.roster_gaps(drivers, raw)
        roster_changed = False
        if gaps:
            roster_changed = _add_driver_stubs(
                raw, gaps, season, client=client, echo=typer.echo
            )

        # --- Bios -----------------------------------------------------------
        do_bio = bio if bio is not None else bool(fetched)
        bio_changed = False
        if do_bio:
            typer.echo("Refreshing career totals + palmarès…")
            bio_changed = refresh_bio.apply(raw, client=client, echo=typer.echo)

    if cal_changes or roster_changed or bio_changed:
        refresh_bio.save_season_json(json_path, raw)
        typer.echo(f"[OK] wrote {json_path.name}")

    if fetched and reprocess:
        rebuild.rebuild_season(settings, season, echo=typer.echo)
    elif fetched:
        typer.echo("Skipping reprocess (--no-reprocess). Run the build before serving.")

    if not (fetched or cal_changes or roster_changed or bio_changed):
        typer.echo(f"Season {season} is up to date — nothing to do.")
