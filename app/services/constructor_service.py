"""Constructor-centric services. Mirror of `driver_service` + the parts of
`championship_service` and `statistics_service` that apply to WCC.

Each helper runs at most one query against the pre-computed constructor
caches. The page-facing layer composes them.
"""
from sqlalchemy import Connection

from app.cache import service as cache
from app.data.queries import constructors as q
from app.services import season_service

# --- module-private cache keys --------------------------------------------


def _key_all_wins(season: int) -> str:
    return f"constructor:all-wins:{season}"


def _key_highest_position(season: int) -> str:
    return f"constructor:highest-position:{season}"


def _key_min_races(season: int) -> str:
    return f"constructor:min-races:{season}"


def _key_win_probability(season: int) -> str:
    return f"constructor:win-probability:{season}"


def _key_positions(position: int, season: int) -> str:
    return f"constructor:positions:{season}:{position}"


def _key_stats(name: str, season: int) -> str:
    return f"constructor:stats:{season}:{name}"


def _key_h2h(a: str, b: str, season: int) -> str:
    x, y = sorted((a, b))
    return f"constructor:h2h:{season}:{x}:{y}"


# --- aggregate pages -------------------------------------------------------


def live_points(conn: Connection, season: int) -> dict[str, int]:
    """Constructor → points in the longest-num_races WCC standing.

    Used to sort the /constructors list page the same way /drivers sorts
    drivers by their live points.
    """
    row = q.latest_for_season(conn, season)
    if not row:
        return {}
    names = [c.strip() for c in row["standings"].split(",")]
    points = [int(p) for p in row["points"].split(",")]
    return dict(zip(names, points, strict=True))


def all_wins(conn: Connection, season: int) -> dict[str, int]:
    def compute():
        rows = q.winner_counts(conn, season)
        return {r["winner"]: int(r["wins"]) for r in rows}
    return cache.get_or_compute(_key_all_wins(season), compute)


def min_races_to_win(conn: Connection, season: int) -> dict[str, int]:
    def compute():
        rows = q.min_races_per_winner(conn, season)
        return {r["winner"]: int(r["min_races"]) for r in rows}
    return cache.get_or_compute(_key_min_races(season), compute)


def highest_position_all(conn: Connection, season: int) -> list[dict]:
    cached = cache.get(_key_highest_position(season))
    if cached is not None:
        return cached
    rows = q.all_statistics(conn, season)
    result = [
        {
            "constructor": r["constructor_name"],
            "position": int(r["highest_position"]),
            "max_races": r["highest_position_max_races"],
            "max_races_championship_id": r["highest_position_championship_id"],
            "best_margin": r["best_margin"],
            "best_margin_championship_id": r["best_margin_championship_id"],
        }
        for r in rows
    ]
    cache.set(_key_highest_position(season), result)
    return result


def win_probability(conn: Connection, season: int) -> dict:
    """Per-constructor × season-length win share — same shape as the
    driver version produced by statistics_service.win_probability."""
    cached = cache.get(_key_win_probability(season))
    if cached is not None:
        return cached

    cache_rows = q.win_probability_cache(conn, season)

    wins_per_length: dict[str, dict[int, int]] = {}
    seasons_per_length: dict[int, int] = {}
    constructor_totals: dict[str, int] = {}

    for r in cache_rows:
        name = r["constructor_name"]
        nr = int(r["num_races"])
        wins = int(r["win_count"])
        total = int(r["total_at_length"])
        wins_per_length.setdefault(name, {})[nr] = wins
        seasons_per_length[nr] = total
        constructor_totals[name] = constructor_totals.get(name, 0) + wins

    season_lengths = sorted(seasons_per_length.keys())
    constructors = sorted(constructor_totals.keys())

    constructors_data = []
    for name in constructors:
        wins_per_len = wins_per_length.get(name, {})
        row_wins = [wins_per_len.get(length, 0) for length in season_lengths]
        percentages = [
            round((wins / seasons_per_length.get(length, 1)) * 100, 2)
            if seasons_per_length.get(length) else 0.0
            for length, wins in zip(season_lengths, row_wins, strict=True)
        ]
        constructors_data.append({
            "constructor": name,
            "total_titles": constructor_totals.get(name, 0),
            "wins_per_length": row_wins,
            "percentages": percentages,
        })

    if constructors_data and season_lengths:
        constructors_data.sort(
            key=lambda d: tuple(reversed(d["percentages"])) if d["percentages"] else (),
            reverse=True,
        )

    result = {
        "season": season,
        "season_lengths": season_lengths,
        "possible_seasons": [
            seasons_per_length.get(length, 0) for length in season_lengths
        ],
        "constructors_data": constructors_data,
    }
    cache.set(_key_win_probability(season), result)
    return result


def position_summary(conn: Connection, position: int, season: int) -> list[dict]:
    def compute():
        rows = q.position_constructor_counts(conn, position, season)
        total = sum(int(r["count"]) for r in rows)
        return [
            {
                "constructor": r["constructor_name"],
                "count": int(r["count"]),
                "percentage": (
                    round((int(r["count"]) / total) * 100, 2) if total else 0.0
                ),
            }
            for r in rows
        ]
    return cache.get_or_compute(_key_positions(position, season), compute)


# --- detail page (used by Commit 3) ---------------------------------------


def _sum_total_championships(seasons_per_length: dict[int, int]) -> int:
    return sum(seasons_per_length.values()) if seasons_per_length else 0


def get_stats(conn: Connection, constructor_name: str, season: int) -> dict:
    key = _key_stats(constructor_name, season)
    cached = cache.get(key)
    if cached is not None:
        return cached

    sd = season_service.get_season_data(season)
    precomputed = q.statistics(conn, constructor_name, season)

    seasons_per_length = cache.get_or_compute(
        f"constructor:seasons-per-length:{season}",
        lambda: q.seasons_per_length(conn, season),
    )
    total_championships = _sum_total_championships(seasons_per_length)

    if precomputed:
        total_wins = int(precomputed["win_count"])
        highest_position = int(precomputed["highest_position"])
        highest_position_cid = precomputed["highest_position_championship_id"]
    else:
        total_wins = q.total_wins(conn, constructor_name, season)
        highest_position = len(sd.teams) or 1
        highest_position_cid = None

    win_pct = (
        round((total_wins / total_championships) * 100, 2)
        if total_championships else 0.0
    )

    min_races = q.min_race_to_win(conn, constructor_name, season)

    wins_by_len = q.wins_by_length(conn, constructor_name, season)
    win_prob = {
        length: round((wins / seasons_per_length.get(length, 1)) * 100, 2)
        for length, wins in wins_by_len.items()
    }

    position_dist = q.position_counts(conn, constructor_name, season)

    h2h_rows = q.head_to_head_against_all(conn, constructor_name, season)
    head_to_head = {
        r["opponent"]: {"wins": int(r["wins"] or 0), "losses": int(r["losses"] or 0)}
        for r in h2h_rows
    }

    result = {
        "constructor_name": constructor_name,
        "slug": season_service.team_slug(constructor_name),
        "color": sd.teams.get(constructor_name, "#666"),
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


def head_to_head(conn: Connection, c1: str, c2: str, season: int) -> dict[str, int]:
    if c1 == c2:
        raise ValueError("Cannot compare a constructor with themselves")
    a, b = sorted((c1, c2))
    key = _key_h2h(a, b, season)
    cached = cache.get(key)
    if cached is None:
        a_wins, b_wins = q.head_to_head_pair(conn, a, b, season)
        cached = {a: a_wins, b: b_wins}
        cache.set(key, cached)
    return {c1: cached[c1], c2: cached[c2]}


def championships_at_position(
    conn: Connection,
    constructor_name: str,
    position: int,
    season: int,
    page: int,
    per_page: int,
) -> dict:
    offset = (page - 1) * per_page

    if position == 1:
        total, rows = q.winner_paginated(
            conn, season, constructor_name, per_page, offset
        )
        championships = [_format_winner_row(r) for r in rows]
    else:
        total, rows = q.position_championships_paginated(
            conn, constructor_name, position, season, per_page, offset
        )
        championships = [_format_position_row(r, position) for r in rows]

    total_pages = (total + per_page - 1) // per_page if total else 1
    return {
        "constructor_name": constructor_name,
        "slug": season_service.team_slug(constructor_name),
        "position": position,
        "total_count": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "championships": championships,
        "season": season,
    }


def _format_winner_row(row: dict) -> dict:
    standings = [c.strip() for c in row["standings"].split(",")]
    points_list = [int(p) for p in row["points"].split(",")]
    pts = points_list[0] if points_list else 0
    margin = points_list[0] - points_list[1] if len(points_list) >= 2 else None
    return {
        "championship_id": int(row["championship_id"]),
        "num_races": int(row["num_races"]),
        "standings": standings,
        "constructor_points": pts,
        "margin": margin,
    }


def _format_position_row(row: dict, position: int) -> dict:
    standings = [c.strip() for c in row["standings"].split(",")]
    points_list = [int(p) for p in row["points"].split(",")]
    pts = int(row["constructor_points"])
    margin = (
        points_list[position - 2] - pts
        if position > 1 and len(points_list) >= position
        else None
    )
    return {
        "championship_id": int(row["championship_id"]),
        "num_races": int(row["num_races"]),
        "standings": standings,
        "constructor_points": pts,
        "margin": margin,
    }
