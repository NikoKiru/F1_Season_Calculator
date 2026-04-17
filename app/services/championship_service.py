"""Championship lookups + formatting.

The big "format_championship_data" function in the old code mixed SQL access,
string splitting, season-config lookups, and round-points CSV reads. Here,
each concern is a separate function — the formatter is pure.
"""
import csv
from typing import Any

from sqlalchemy import Connection

from app.cache import service as cache
from app.config import get_settings
from app.data.queries import championships as q
from app.services import season_service


def _parse_csv_list(raw: str, cast=str) -> list:
    if not raw:
        return []
    return [cast(x.strip()) for x in raw.split(",")]


def _format(row: dict, season: int, *, with_round_points: bool = False) -> dict:
    """Decorate a raw championship row with names + derived fields."""
    sd = season_service.get_season_data(season)
    result = dict(row)

    if row.get("rounds"):
        round_numbers = _parse_csv_list(row["rounds"], int)
        result["round_names"] = [sd.round_names.get(r, "Unknown") for r in round_numbers]

    if row.get("standings") and row.get("points"):
        drivers = _parse_csv_list(row["standings"])
        points = _parse_csv_list(row["points"], int)
        result["driver_points"] = dict(zip(drivers, points))
        result["driver_names"] = {d: sd.driver_names.get(d, "Unknown") for d in drivers}

        if with_round_points and row.get("rounds"):
            round_numbers = _parse_csv_list(row["rounds"], int)
            result["round_points_data"] = _round_points(drivers, round_numbers, season)

    return result


def _round_points(drivers: list[str], round_numbers: list[int], season: int) -> dict[str, Any]:
    """Per-driver per-round points for the championship detail page.

    Reads the season CSV once. Small (≤ 22 drivers × ≤ 24 rounds) so no perf concern.
    """
    path = _season_csv_path(season)
    if path is None:
        return {}

    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        available = set((reader.fieldnames or [])) - {"Driver"}
        round_cols = [str(r) for r in round_numbers if str(r) in available]
        by_driver: dict[str, list[int]] = {}
        for row in reader:
            name = row["Driver"].strip()
            if name in drivers:
                by_driver[name] = [int(row[c]) for c in round_cols]

    out: dict[str, Any] = {}
    for d in drivers:
        pts = by_driver.get(d, [])
        out[d] = {"round_points": pts, "total_points": sum(pts)}
    return out


def _season_csv_path(season: int):
    folder = get_settings().data_folder
    specific = folder / f"championships_{season}.csv"
    if specific.exists():
        return specific
    generic = folder / "championships.csv"
    if generic.exists():
        return generic
    return None


# --- public API ------------------------------------------------------------

def get_page(conn: Connection, season: int, page: int, per_page: int) -> dict:
    total = q.count_for_season(conn, season)
    offset = (page - 1) * per_page
    rows = q.page(conn, season, per_page, offset)
    total_pages = (total + per_page - 1) // per_page if total else 0
    return {
        "total_results": total,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        "season": season,
        "next_page": (
            f"/api/championships?page={page + 1}&per_page={per_page}&season={season}"
            if page < total_pages else None
        ),
        "prev_page": (
            f"/api/championships?page={page - 1}&per_page={per_page}&season={season}"
            if page > 1 else None
        ),
        "results": [_format(r, season) for r in rows],
    }


def get_by_id(conn: Connection, championship_id: int) -> dict | None:
    cached = cache.get(cache.key_championship(championship_id))
    if cached is not None:
        return cached
    row = q.by_id(conn, championship_id)
    if row is None:
        return None
    formatted = _format(row, int(row["season"]), with_round_points=True)
    cache.set(cache.key_championship(championship_id), formatted)
    return formatted


def find_by_rounds(conn: Connection, rounds: list[int], season: int) -> int | None:
    """Returns championship_id if the exact round combination exists for this season."""
    sorted_rounds = sorted(set(rounds))
    csv_str = ",".join(str(r) for r in sorted_rounds)
    key = cache.key_search_rounds(csv_str, season)
    cached = cache.get(key)
    if cached is not None:
        return cached if cached != 0 else None
    row = q.by_rounds(conn, csv_str, season)
    cid = int(row["championship_id"]) if row else None
    cache.set(key, cid if cid is not None else 0)
    return cid


def all_wins(conn: Connection, season: int) -> dict[str, int]:
    def compute():
        rows = q.winner_counts(conn, season)
        return {r["winner"]: int(r["wins"]) for r in rows}
    return cache.get_or_compute(cache.key_all_wins(season), compute)


def min_races_to_win(conn: Connection, season: int) -> dict[str, int]:
    def compute():
        rows = q.min_races_per_winner(conn, season)
        return {r["winner"]: int(r["min_races"]) for r in rows}
    return cache.get_or_compute(cache.key_min_races_to_win(season), compute)
