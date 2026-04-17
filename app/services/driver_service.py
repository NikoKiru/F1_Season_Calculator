"""Driver-centric services.

The old /api/driver/{code}/stats fired 7 sequential queries. Here, each
helper runs exactly one query; the top-level `get_stats` composes them and
caches the assembled result. Still fewer trips per request than the old code
(5 queries, all indexed, vs 7 + unindexed COUNT) and every piece is testable
in isolation.
"""
from sqlalchemy import Connection

from app.cache import service as cache
from app.data.queries import championships as q_c
from app.data.queries import drivers as q_d
from app.data.queries import statistics as q_s
from app.services import season_service


def _sum_total_championships(seasons_per_length: dict[int, int]) -> int:
    return sum(seasons_per_length.values()) if seasons_per_length else 0


def get_stats(conn: Connection, driver_code: str, season: int) -> dict:
    key = cache.key_driver_stats(driver_code, season)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sd = season_service.get_season_data(season)

    # One query for pre-computed stats (INSTANT path)
    precomputed = q_s.driver_statistics(conn, driver_code, season)

    # Shared across all drivers — cached separately
    seasons_per_length = cache.get_or_compute(
        f"seasons-per-length:{season}",
        lambda: q_c.seasons_per_length(conn, season),
    )
    total_championships = _sum_total_championships(seasons_per_length)

    if precomputed:
        total_wins = int(precomputed["win_count"])
        highest_position = int(precomputed["highest_position"])
        highest_position_cid = precomputed["highest_position_championship_id"]
    else:
        total_wins = q_d.total_wins(conn, driver_code, season)
        highest_position = 20
        highest_position_cid = None

    win_pct = round((total_wins / total_championships) * 100, 2) if total_championships else 0.0

    min_races = q_d.min_race_to_win(conn, driver_code, season)

    wins_by_len = q_d.wins_by_length(conn, driver_code, season)
    win_prob = {
        length: round((wins / seasons_per_length.get(length, 1)) * 100, 2)
        for length, wins in wins_by_len.items()
    }

    position_dist = q_d.position_counts(conn, driver_code, season)

    h2h_rows = q_d.head_to_head_against_all(conn, driver_code, season)
    head_to_head = {
        r["opponent"]: {"wins": int(r["wins"] or 0), "losses": int(r["losses"] or 0)}
        for r in h2h_rows
    }

    result = {
        "driver_code": driver_code,
        "driver_name": sd.driver_names[driver_code],
        "driver_info": sd.drivers[driver_code].model_dump(),
        "total_wins": total_wins,
        "total_championships": total_championships,
        "win_percentage": win_pct,
        "highest_position": highest_position,
        "highest_position_championship_id": highest_position_cid,
        "min_races_to_win": min_races,
        "position_distribution": position_dist,
        "win_probability_by_length": win_prob,
        "seasons_per_length": seasons_per_length,
        "head_to_head": head_to_head,
        "season": season,
    }
    cache.set(key, result)
    return result


def head_to_head(conn: Connection, d1: str, d2: str, season: int) -> dict[str, int]:
    """{d1: d1_wins, d2: d2_wins} — keys preserved in request order for display."""
    if d1 == d2:
        raise ValueError("Cannot compare a driver with themselves")

    a, b = sorted((d1, d2))
    key = cache.key_head_to_head(a, b, season)
    cached = cache.get(key)
    if cached is None:
        a_wins, b_wins = q_d.head_to_head_pair(conn, a, b, season)
        cached = {a: a_wins, b: b_wins}
        cache.set(key, cached)
    # Return keys in request order
    return {d1: cached[d1], d2: cached[d2]}


def position_summary(conn: Connection, position: int, season: int) -> list[dict]:
    def compute():
        rows = q_d.position_driver_counts(conn, position, season)
        total = sum(int(r["count"]) for r in rows)
        return [
            {
                "driver": r["driver_code"],
                "count": int(r["count"]),
                "percentage": round((int(r["count"]) / total) * 100, 2) if total else 0.0,
            }
            for r in rows
        ]
    return cache.get_or_compute(cache.key_driver_positions(position, season), compute)


def championships_at_position(
    conn: Connection,
    driver_code: str,
    position: int,
    season: int,
    page: int,
    per_page: int,
) -> dict:
    sd = season_service.get_season_data(season)
    offset = (page - 1) * per_page

    if position == 1:
        total, rows = q_c.driver_wins_paginated(conn, season, driver_code, per_page, offset)
        championships = [_format_winner_row(r) for r in rows]
    else:
        total, rows = q_d.position_championships_paginated(
            conn, driver_code, position, season, per_page, offset
        )
        championships = [_format_position_row(r, position) for r in rows]

    total_pages = (total + per_page - 1) // per_page if total else 1
    return {
        "driver_code": driver_code,
        "driver_name": sd.driver_names.get(driver_code, driver_code),
        "position": position,
        "total_count": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "championships": championships,
        "season": season,
    }


def _format_winner_row(row: dict) -> dict:
    standings = [d.strip() for d in row["standings"].split(",")]
    points_list = [int(p) for p in row["points"].split(",")]
    driver_points = points_list[0] if points_list else 0
    margin = points_list[0] - points_list[1] if len(points_list) >= 2 else None
    return {
        "championship_id": int(row["championship_id"]),
        "num_races": int(row["num_races"]),
        "standings": standings,
        "driver_points": driver_points,
        "margin": margin,
    }


def _format_position_row(row: dict, position: int) -> dict:
    standings = [d.strip() for d in row["standings"].split(",")]
    points_list = [int(p) for p in row["points"].split(",")]
    driver_points = int(row["driver_points"])
    margin = (
        points_list[position - 2] - driver_points
        if position > 1 and len(points_list) >= position
        else None
    )
    return {
        "championship_id": int(row["championship_id"]),
        "num_races": int(row["num_races"]),
        "standings": standings,
        "driver_points": driver_points,
        "margin": margin,
    }


def highest_position_all(conn: Connection, season: int) -> list[dict]:
    key = cache.key_highest_position(season)
    cached = cache.get(key)
    if cached is not None:
        return cached
    rows = q_s.all_driver_statistics(conn, season)
    result = [
        {
            "driver": r["driver_code"],
            "position": int(r["highest_position"]),
            "max_races": r["highest_position_max_races"],
            "max_races_championship_id": r["highest_position_championship_id"],
            "best_margin": r["best_margin"],
            "best_margin_championship_id": r["best_margin_championship_id"],
        }
        for r in rows
    ]
    cache.set(key, result)
    return result
