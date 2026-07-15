"""SQL queries against the constructor_* tables. Mirrors the driver-side
queries split across `championships.py`, `drivers.py`, and `statistics.py`,
consolidated here since the constructor namespace is self-contained.
"""
from sqlalchemy import Connection, text

# --- championship_results-equivalent --------------------------------------


def count_for_season(conn: Connection, season: int) -> int:
    row = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM constructor_championship_results "
            "WHERE season = :s"
        ),
        {"s": season},
    ).one()
    return int(row.c)


def by_id(conn: Connection, championship_id: int) -> dict | None:
    row = conn.execute(
        text(
            "SELECT championship_id, season, num_races, rounds, standings, "
            "       winner, points "
            "FROM constructor_championship_results "
            "WHERE championship_id = :id"
        ),
        {"id": championship_id},
    ).mappings().one_or_none()
    return dict(row) if row else None


def latest_for_season(conn: Connection, season: int) -> dict | None:
    """The longest-num_races championship — used as the 'live' WCC standing."""
    row = conn.execute(
        text(
            "SELECT championship_id, season, num_races, rounds, standings, "
            "       winner, points "
            "FROM constructor_championship_results "
            "WHERE season = :s "
            "ORDER BY num_races DESC, championship_id ASC LIMIT 1"
        ),
        {"s": season},
    ).mappings().one_or_none()
    return dict(row) if row else None


def winner_counts(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT winner, COUNT(*) AS wins FROM constructor_championship_results "
            "WHERE winner IS NOT NULL AND season = :s "
            "GROUP BY winner ORDER BY wins DESC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def min_races_per_winner(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT winner, MIN(num_races) AS min_races "
            "FROM constructor_championship_results "
            "WHERE winner IS NOT NULL AND season = :s "
            "GROUP BY winner ORDER BY min_races ASC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def seasons_per_length(conn: Connection, season: int) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT num_races, COUNT(*) AS total "
            "FROM constructor_championship_results "
            "WHERE season = :s GROUP BY num_races"
        ),
        {"s": season},
    ).mappings().all()
    return {int(r["num_races"]): int(r["total"]) for r in rows}


def winner_paginated(
    conn: Connection, season: int, constructor_name: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    total = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM constructor_championship_results "
            "WHERE winner = :c AND season = :s"
        ),
        {"c": constructor_name, "s": season},
    ).one().c
    rows = conn.execute(
        text(
            "SELECT championship_id, num_races, rounds, standings, points "
            "FROM constructor_championship_results "
            "WHERE winner = :c AND season = :s "
            "ORDER BY num_races DESC, championship_id DESC LIMIT :lim OFFSET :off"
        ),
        {"c": constructor_name, "s": season, "lim": limit, "off": offset},
    ).mappings().all()
    return int(total), [dict(r) for r in rows]


# --- driver_statistics-equivalent -----------------------------------------


def statistics(conn: Connection, constructor_name: str, season: int) -> dict | None:
    row = conn.execute(
        text(
            "SELECT highest_position, highest_position_max_races, "
            "       highest_position_championship_id, best_margin, "
            "       best_margin_championship_id, win_count "
            "FROM constructor_statistics "
            "WHERE constructor_name = :c AND season = :s"
        ),
        {"c": constructor_name, "s": season},
    ).mappings().one_or_none()
    return dict(row) if row else None


def all_statistics(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT constructor_name, highest_position, highest_position_max_races, "
            "       highest_position_championship_id, best_margin, "
            "       best_margin_championship_id, win_count "
            "FROM constructor_statistics WHERE season = :s "
            "ORDER BY highest_position ASC, win_count DESC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def win_probability_cache(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT constructor_name, num_races, win_count, total_at_length "
            "FROM constructor_win_probability_cache WHERE season = :s "
            "ORDER BY constructor_name, num_races"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


# --- driver_head_to_head + driver_position_distribution-equivalent ---------


def head_to_head_against_all(
    conn: Connection, constructor_name: str, season: int
) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT opponent, wins, losses FROM constructor_head_to_head "
            "WHERE season = :s AND constructor_name = :c ORDER BY opponent"
        ),
        {"c": constructor_name, "s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def head_to_head_pair(
    conn: Connection, c1: str, c2: str, season: int
) -> tuple[int, int]:
    row = conn.execute(
        text(
            "SELECT wins, losses FROM constructor_head_to_head "
            "WHERE season = :s AND constructor_name = :c1 AND opponent = :c2"
        ),
        {"c1": c1, "c2": c2, "s": season},
    ).one_or_none()
    if row is None:
        return 0, 0
    return int(row.wins), int(row.losses)


def position_counts(
    conn: Connection, constructor_name: str, season: int
) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT position, count AS cnt "
            "FROM constructor_position_distribution "
            "WHERE constructor_name = :c AND season = :s ORDER BY position"
        ),
        {"c": constructor_name, "s": season},
    ).mappings().all()
    return {int(r["position"]): int(r["cnt"]) for r in rows}


def position_constructor_counts(
    conn: Connection, position: int, season: int
) -> list[dict]:
    """Live aggregation fallback — see position_constructor_counts_from_distribution."""
    rows = conn.execute(
        text(
            "SELECT constructor_name, COUNT(*) AS count "
            "FROM constructor_position_results "
            "WHERE position = :p AND season = :s "
            "GROUP BY constructor_name ORDER BY count DESC"
        ),
        {"p": position, "s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def position_constructor_counts_from_distribution(
    conn: Connection, position: int, season: int
) -> list[dict]:
    """Indexed lookup in the precomputed `constructor_position_distribution`
    cache. Same shape as the live aggregation; empty before compute-stats."""
    rows = conn.execute(
        text(
            "SELECT constructor_name, count AS cnt "
            "FROM constructor_position_distribution "
            "WHERE season = :s AND position = :p ORDER BY cnt DESC"
        ),
        {"p": position, "s": season},
    ).mappings().all()
    return [
        {"constructor_name": r["constructor_name"], "count": int(r["cnt"])}
        for r in rows
    ]


def position_championships_paginated(
    conn: Connection,
    constructor_name: str,
    position: int,
    season: int,
    limit: int,
    offset: int,
) -> tuple[int, list[dict]]:
    total = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM constructor_position_results "
            "WHERE constructor_name = :c AND position = :p AND season = :s"
        ),
        {"c": constructor_name, "p": position, "s": season},
    ).one().c
    rows = conn.execute(
        text(
            "SELECT cr.championship_id, cr.num_races, cr.rounds, cr.standings, "
            "       cr.points, pr.points AS constructor_points "
            "FROM constructor_position_results pr "
            "JOIN constructor_championship_results cr "
            "  ON pr.championship_id = cr.championship_id "
            "WHERE pr.constructor_name = :c AND pr.position = :p AND pr.season = :s "
            "ORDER BY cr.num_races DESC, cr.championship_id DESC "
            "LIMIT :lim OFFSET :off"
        ),
        {
            "c": constructor_name, "p": position, "s": season,
            "lim": limit, "off": offset,
        },
    ).mappings().all()
    return int(total), [dict(r) for r in rows]


def wins_by_length(
    conn: Connection, constructor_name: str, season: int
) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT num_races, COUNT(*) AS wins "
            "FROM constructor_championship_results "
            "WHERE winner = :c AND season = :s GROUP BY num_races"
        ),
        {"c": constructor_name, "s": season},
    ).mappings().all()
    return {int(r["num_races"]): int(r["wins"]) for r in rows}


def min_race_to_win(conn: Connection, constructor_name: str, season: int) -> int | None:
    row = conn.execute(
        text(
            "SELECT MIN(num_races) AS m FROM constructor_championship_results "
            "WHERE winner = :c AND season = :s"
        ),
        {"c": constructor_name, "s": season},
    ).one()
    return int(row.m) if row.m is not None else None


def total_wins(conn: Connection, constructor_name: str, season: int) -> int:
    row = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM constructor_championship_results "
            "WHERE winner = :c AND season = :s"
        ),
        {"c": constructor_name, "s": season},
    ).one()
    return int(row.c)
