from sqlalchemy import Connection, text


def count_for_season(conn: Connection, season: int) -> int:
    row = conn.execute(
        text("SELECT COUNT(*) AS c FROM championship_results WHERE season = :s"),
        {"s": season},
    ).one()
    return int(row.c)


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
        text(
            "SELECT championship_id FROM championship_results "
            "WHERE rounds = :r AND season = :s"
        ),
        {"r": rounds_csv, "s": season},
    ).mappings().one_or_none()
    return dict(row) if row else None


def winner_counts(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT winner, COUNT(*) AS wins FROM championship_results "
            "WHERE winner IS NOT NULL AND season = :s "
            "GROUP BY winner ORDER BY wins DESC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def min_races_per_winner(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT winner, MIN(num_races) AS min_races FROM championship_results "
            "WHERE winner IS NOT NULL AND season = :s "
            "GROUP BY winner ORDER BY min_races ASC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def seasons_per_length(conn: Connection, season: int) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT num_races, COUNT(*) AS total FROM championship_results "
            "WHERE season = :s GROUP BY num_races"
        ),
        {"s": season},
    ).mappings().all()
    return {int(r["num_races"]): int(r["total"]) for r in rows}


def driver_wins_paginated(
    conn: Connection, season: int, driver_code: str, limit: int, offset: int
) -> tuple[int, list[dict]]:
    """Position 1 case — uses the indexed `winner` column."""
    total = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM championship_results "
            "WHERE winner = :d AND season = :s"
        ),
        {"d": driver_code, "s": season},
    ).one().c
    rows = conn.execute(
        text(
            "SELECT championship_id, num_races, rounds, standings, points "
            "FROM championship_results WHERE winner = :d AND season = :s "
            "ORDER BY num_races DESC, championship_id DESC LIMIT :lim OFFSET :off"
        ),
        {"d": driver_code, "s": season, "lim": limit, "off": offset},
    ).mappings().all()
    return int(total), [dict(r) for r in rows]
