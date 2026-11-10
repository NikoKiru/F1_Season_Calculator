"""Queries on championship_results.

The per-season aggregates read `win_probability_cache`, which holds one row
per driver and season length. Counting over championship_results instead is a
pass over the whole season on every request. Each aggregate keeps that count
as its fallback, for a season whose stats haven't been computed yet.
"""
from sqlalchemy import Connection, text

# `+season` keeps the planner off the season indexes. Without statistics they
# look as selective as idx_rounds, and it then filters the whole season.
BY_ROUNDS = (
    "SELECT championship_id FROM championship_results "
    "WHERE rounds = :r AND +season = :s"
)


def page(conn: Connection, season: int, limit: int, offset: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT championship_id, season, num_races, rounds, standings, winner, points "
            "FROM championship_results WHERE season = :s "
            "ORDER BY num_races DESC, championship_id ASC LIMIT :lim OFFSET :off"
        ),
        {"s": season, "lim": limit, "off": offset},
    ).mappings().all()
    return [dict(r) for r in rows]


def by_id(conn: Connection, championship_id: int) -> dict | None:
    row = conn.execute(
        text(
            "SELECT championship_id, season, num_races, rounds, standings, winner, points "
            "FROM championship_results WHERE championship_id = :id"
        ),
        {"id": championship_id},
    ).mappings().one_or_none()
    return dict(row) if row else None


def by_rounds(conn: Connection, rounds_csv: str, season: int) -> dict | None:
    row = conn.execute(
        text(BY_ROUNDS), {"r": rounds_csv, "s": season}
    ).mappings().one_or_none()
    return dict(row) if row else None


def winner_counts(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT driver_code AS winner, SUM(win_count) AS wins "
            "FROM win_probability_cache WHERE season = :s "
            "GROUP BY driver_code HAVING SUM(win_count) > 0 "
            "ORDER BY wins DESC, winner"
        ),
        {"s": season},
    ).mappings().all()
    if not rows:
        rows = conn.execute(
            text(
                "SELECT winner, COUNT(*) AS wins FROM championship_results "
                "WHERE winner IS NOT NULL AND season = :s "
                "GROUP BY winner ORDER BY wins DESC, winner"
            ),
            {"s": season},
        ).mappings().all()
    return [dict(r) for r in rows]


def min_races_per_winner(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT driver_code AS winner, MIN(num_races) AS min_races "
            "FROM win_probability_cache WHERE season = :s AND win_count > 0 "
            "GROUP BY driver_code ORDER BY min_races ASC, winner"
        ),
        {"s": season},
    ).mappings().all()
    if not rows:
        rows = conn.execute(
            text(
                "SELECT winner, MIN(num_races) AS min_races FROM championship_results "
                "WHERE winner IS NOT NULL AND season = :s "
                "GROUP BY winner ORDER BY min_races ASC, winner"
            ),
            {"s": season},
        ).mappings().all()
    return [dict(r) for r in rows]


def seasons_per_length(conn: Connection, season: int) -> dict[int, int]:
    """Scenario count per season length. Every cache row of a length carries it."""
    rows = conn.execute(
        text(
            "SELECT num_races, MAX(total_at_length) AS total "
            "FROM win_probability_cache WHERE season = :s GROUP BY num_races"
        ),
        {"s": season},
    ).mappings().all()
    if not rows:
        rows = conn.execute(
            text(
                "SELECT num_races, COUNT(*) AS total FROM championship_results "
                "WHERE season = :s GROUP BY num_races"
            ),
            {"s": season},
        ).mappings().all()
    return {int(r["num_races"]): int(r["total"]) for r in rows}


def driver_wins_paginated(
    conn: Connection,
    season: int,
    driver_code: str,
    limit: int,
    offset: int,
    num_races: int | None = None,
) -> tuple[int, list[dict]]:
    """Position 1 case — uses the indexed `winner` column."""
    length = "" if num_races is None else "AND num_races = :n "
    params = {"d": driver_code, "s": season}
    if num_races is not None:
        params["n"] = num_races
    total = conn.execute(
        text(
            "SELECT COALESCE("
            "  (SELECT SUM(win_count) FROM win_probability_cache "
            f"  WHERE driver_code = :d AND season = :s {length}), "
            "  (SELECT COUNT(*) FROM championship_results "
            f"  WHERE winner = :d AND season = :s {length})"
            ") AS c"
        ),
        params,
    ).one().c
    rows = conn.execute(
        text(
            "SELECT championship_id, num_races, rounds, standings, points "
            f"FROM championship_results WHERE winner = :d AND season = :s {length}"
            "ORDER BY num_races DESC, championship_id DESC LIMIT :lim OFFSET :off"
        ),
        {**params, "lim": limit, "off": offset},
    ).mappings().all()
    return int(total), [dict(r) for r in rows]
