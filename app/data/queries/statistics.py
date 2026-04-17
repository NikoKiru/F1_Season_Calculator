from sqlalchemy import Connection, text


def driver_statistics(conn: Connection, driver_code: str, season: int) -> dict | None:
    row = conn.execute(
        text(
            "SELECT highest_position, highest_position_max_races, "
            "       highest_position_championship_id, best_margin, "
            "       best_margin_championship_id, win_count "
            "FROM driver_statistics "
            "WHERE driver_code = :d AND season = :s"
        ),
        {"d": driver_code, "s": season},
    ).mappings().one_or_none()
    return dict(row) if row else None


def all_driver_statistics(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT driver_code, highest_position, highest_position_max_races, "
            "       highest_position_championship_id, best_margin, "
            "       best_margin_championship_id, win_count "
            "FROM driver_statistics WHERE season = :s "
            "ORDER BY highest_position ASC, win_count DESC"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]


def win_probability_cache(conn: Connection, season: int) -> list[dict]:
    rows = conn.execute(
        text(
            "SELECT driver_code, num_races, win_count, total_at_length "
            "FROM win_probability_cache WHERE season = :s "
            "ORDER BY driver_code, num_races"
        ),
        {"s": season},
    ).mappings().all()
    return [dict(r) for r in rows]
