from sqlalchemy import Connection, text


def position_counts(conn: Connection, driver_code: str, season: int) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT position, COUNT(*) AS cnt FROM position_results "
            "WHERE driver_code = :d AND season = :s "
            "GROUP BY position ORDER BY position"
        ),
        {"d": driver_code, "s": season},
    ).mappings().all()
    return {int(r["position"]): int(r["cnt"]) for r in rows}


def wins_by_length(conn: Connection, driver_code: str, season: int) -> dict[int, int]:
    rows = conn.execute(
        text(
            "SELECT num_races, COUNT(*) AS wins FROM championship_results "
            "WHERE winner = :d AND season = :s GROUP BY num_races"
        ),
        {"d": driver_code, "s": season},
    ).mappings().all()
    return {int(r["num_races"]): int(r["wins"]) for r in rows}


def min_race_to_win(conn: Connection, driver_code: str, season: int) -> int | None:
    row = conn.execute(
        text(
            "SELECT MIN(num_races) AS m FROM championship_results "
            "WHERE winner = :d AND season = :s"
        ),
        {"d": driver_code, "s": season},
    ).one()
    return int(row.m) if row.m is not None else None


def total_wins(conn: Connection, driver_code: str, season: int) -> int:
    row = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM championship_results "
            "WHERE winner = :d AND season = :s"
        ),
        {"d": driver_code, "s": season},
    ).one()
    return int(row.c)


def head_to_head_against_all(conn: Connection, driver_code: str, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT pr2.driver_code AS opponent, "
            "SUM(CASE WHEN pr1.position < pr2.position THEN 1 ELSE 0 END) AS wins, "
            "SUM(CASE WHEN pr1.position > pr2.position THEN 1 ELSE 0 END) AS losses "
            "FROM position_results pr1 "
            "JOIN position_results pr2 ON pr1.championship_id = pr2.championship_id "
            "  AND pr1.season = pr2.season "
            "WHERE pr1.driver_code = :d AND pr1.season = :s AND pr2.driver_code != :d "
            "GROUP BY pr2.driver_code"
        ),
        {"d": driver_code, "s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def head_to_head_pair(conn: Connection, d1: str, d2: str, season: int) -> tuple[int, int]:
    row = conn.execute(
        text(
            "SELECT "
            "SUM(CASE WHEN p1.position < p2.position THEN 1 ELSE 0 END) AS d1_wins, "
            "SUM(CASE WHEN p1.position > p2.position THEN 1 ELSE 0 END) AS d2_wins "
            "FROM position_results p1 "
            "JOIN position_results p2 ON p1.championship_id = p2.championship_id "
            "  AND p1.season = p2.season "
            "WHERE p1.driver_code = :d1 AND p2.driver_code = :d2 AND p1.season = :s"
        ),
        {"d1": d1, "d2": d2, "s": season},
    ).one()
    return int(row.d1_wins or 0), int(row.d2_wins or 0)


def position_driver_counts(conn: Connection, position: int, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT driver_code, COUNT(*) AS count FROM position_results "
            "WHERE position = :p AND season = :s "
            "GROUP BY driver_code ORDER BY count DESC"
        ),
        {"p": position, "s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def position_championships_paginated(
    conn: Connection, driver_code: str, position: int, season: int, limit: int, offset: int
) -> tuple[int, list[dict]]:
    total = conn.execute(
        text(
            "SELECT COUNT(*) AS c FROM position_results "
            "WHERE driver_code = :d AND position = :p AND season = :s"
        ),
        {"d": driver_code, "p": position, "s": season},
    ).one().c
    rows = conn.execute(
        text(
            "SELECT cr.championship_id, cr.num_races, cr.rounds, cr.standings, cr.points, "
            "       pr.points AS driver_points "
            "FROM position_results pr "
            "JOIN championship_results cr ON pr.championship_id = cr.championship_id "
            "WHERE pr.driver_code = :d AND pr.position = :p AND pr.season = :s "
            "ORDER BY cr.num_races DESC, cr.championship_id DESC "
            "LIMIT :lim OFFSET :off"
        ),
        {"d": driver_code, "p": position, "s": season, "lim": limit, "off": offset},
    ).mappings().all()
    return int(total), [dict(r) for r in rows]
