"""Championship win-probability matrix.

Uses the pre-computed `win_probability_cache` table when available; falls
back to live aggregation only if the cache is missing (should only happen
before compute-stats has run for a new season).
"""
import json

from sqlalchemy import Connection

from app.cache import service as cache
from app.data.queries import championships as q_c
from app.data.queries import statistics as q_s
from app.services import championship_service, season_service


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
            for length, wins in zip(season_lengths, row_wins, strict=True)
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


_NOTABLE_CARD_ORDER = (
    "nail_biter",
    "demolition",
    "against_all_odds",
    "cinderella",
    "kingmaker",
)


def _scenario_summary(conn: Connection, sd, cid: int | None) -> dict | None:
    """Resolve a championship_id to display fields: winner/runner-up names,
    colours, margin, round names. Reuses the cached championship formatter."""
    if cid is None:
        return None
    champ = championship_service.get_by_id(conn, cid)
    if not champ:
        return None
    driver_points = champ.get("driver_points", {}) or {}
    names = champ.get("driver_names", {}) or {}
    codes = list(driver_points)
    winner_code = codes[0] if codes else champ.get("winner")
    runner_up_code = codes[1] if len(codes) > 1 else None
    margin = (
        int(driver_points[winner_code]) - int(driver_points[runner_up_code])
        if runner_up_code is not None
        else 0
    )

    def _color(code: str | None) -> str:
        d = sd.drivers.get(code) if code else None
        return d.color if d else "#666"

    return {
        "id": cid,
        "num_races": champ.get("num_races"),
        "winner_code": winner_code,
        "winner_name": names.get(winner_code, winner_code),
        "winner_color": _color(winner_code),
        "runner_up_code": runner_up_code,
        "runner_up_name": names.get(runner_up_code) if runner_up_code else None,
        "margin": margin,
        "round_names": champ.get("round_names", []),
    }


def notable_scenarios(conn: Connection, season: int) -> dict:
    """Curated "hall of fame of what-ifs" for a season.

    Reads the precomputed `notable_scenarios` table and decorates each category
    with the linked championship (winner/runner-up names, margin, rounds) plus
    a small per-category `extra` block for rendering.
    """
    key = cache.key_notable_scenarios(season)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sd = season_service.get_season_data(season)
    raw = {r["category"]: r for r in q_s.notable_scenarios(conn, season)}

    scenarios = []
    for category in _NOTABLE_CARD_ORDER:
        row = raw.get(category)
        if row is None:
            continue
        headline = _scenario_summary(conn, sd, row["championship_id"])
        if headline is None:
            continue
        detail = json.loads(row["detail"]) if row["detail"] else {}
        extra: dict = {}
        if category == "against_all_odds":
            rc = detail.get("real_champion")
            extra["real_champion_name"] = sd.driver_names.get(rc, rc)
        elif category == "cinderella":
            code = detail.get("driver_code")
            d = sd.drivers.get(code)
            extra.update({
                "driver_code": code,
                "driver_name": sd.driver_names.get(code, code),
                "driver_color": d.color if d else "#666",
            })
        elif category == "kingmaker":
            before = _scenario_summary(conn, sd, detail.get("before_cid"))
            rnd = detail.get("round")
            extra.update({
                "round": rnd,
                "round_name": sd.round_names.get(rnd, f"Round {rnd}"),
                "before_id": detail.get("before_cid"),
                "before_winner_name": before["winner_name"] if before else None,
                "after_winner_name": headline["winner_name"],
            })
        scenarios.append({
            "category": category,
            "championship_id": row["championship_id"],
            "metric_value": row["metric_value"],
            "detail": detail,
            "headline": headline,
            "extra": extra,
        })

    result = {"season": season, "scenarios": scenarios}
    cache.set(key, result)
    return result
