"""Championship win-probability matrix.

Uses the pre-computed `win_probability_cache` table when available; falls
back to live aggregation only if the cache is missing (should only happen
before compute-stats has run for a new season).
"""
from sqlalchemy import Connection

from app.cache import service as cache
from app.data.queries import championships as q_c
from app.data.queries import statistics as q_s
from app.services import season_service


def win_probability(conn: Connection, season: int) -> dict:
    key = cache.key_win_probability(season)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sd = season_service.get_season_data(season)
    cache_rows = q_s.win_probability_cache(conn, season)

    wins_per_length: dict[str, dict[int, int]] = {}
    seasons_per_length: dict[int, int] = {}
    driver_totals: dict[str, int] = {}

    if cache_rows:
        for r in cache_rows:
            driver = r["driver_code"]
            nr = int(r["num_races"])
            wins = int(r["win_count"])
            total = int(r["total_at_length"])
            wins_per_length.setdefault(driver, {})[nr] = wins
            seasons_per_length[nr] = total
            driver_totals[driver] = driver_totals.get(driver, 0) + wins
    else:
        seasons_per_length = q_c.seasons_per_length(conn, season)
        for r in q_c.winner_counts(conn, season):
            driver_totals[r["winner"]] = int(r["wins"])
        # Rebuild wins_per_length via a single aggregation — acceptable slow path.
        from sqlalchemy import text
        rows = conn.execute(
            text(
                "SELECT winner, num_races, COUNT(*) AS wins "
                "FROM championship_results WHERE winner IS NOT NULL AND season = :s "
                "GROUP BY winner, num_races"
            ),
            {"s": season},
        ).mappings().all()
        for r in rows:
            wins_per_length.setdefault(r["winner"], {})[int(r["num_races"])] = int(r["wins"])

    season_lengths = sorted(seasons_per_length.keys())
    drivers = sorted(driver_totals.keys())

    drivers_data = []
    for driver in drivers:
        wins_per_len = wins_per_length.get(driver, {})
        row_wins = [wins_per_len.get(length, 0) for length in season_lengths]
        percentages = [
            round((wins / seasons_per_length.get(length, 1)) * 100, 2) if seasons_per_length.get(length) else 0.0
            for length, wins in zip(season_lengths, row_wins)
        ]
        drivers_data.append({
            "driver": driver,
            "total_titles": driver_totals.get(driver, 0),
            "wins_per_length": row_wins,
            "percentages": percentages,
        })

    # Sort by right-to-left percentages (longest season matters most)
    if drivers_data and season_lengths:
        drivers_data.sort(
            key=lambda d: tuple(reversed(d["percentages"])) if d["percentages"] else (),
            reverse=True,
        )

    result = {
        "season": season,
        "season_lengths": season_lengths,
        "possible_seasons": [seasons_per_length.get(length, 0) for length in season_lengths],
        "drivers_data": drivers_data,
        "driver_names": sd.driver_names,
    }
    cache.set(key, result)
    return result
