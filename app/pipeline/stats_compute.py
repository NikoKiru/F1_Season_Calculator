"""Pre-compute driver_statistics and win_probability_cache for a season.

These tables turn the three expensive aggregations (highest position, best
margin, win-probability-by-length) into O(1) lookups for the API layer.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable


# Just the head-to-head table — running every SCHEMA_STATEMENTS would force
# CREATE INDEX IF NOT EXISTS on position_results (335M rows on prod), which is
# a full-table scan if any index is missing. CREATE on an empty new table and
# its index is instant.
_HEAD_TO_HEAD_DDL = (
    """
    CREATE TABLE IF NOT EXISTS driver_head_to_head (
        season INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        opponent TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (season, driver_code, opponent)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_h2h_season_driver ON driver_head_to_head (season, driver_code)",
    """
    CREATE TABLE IF NOT EXISTS driver_position_distribution (
        season INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        position INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (season, driver_code, position)
    )
    """,
)


def compute(
    db_path: Path,
    season: int,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Populate driver_statistics + win_probability_cache for `season`.

    Returns a small summary dict: {'drivers': n, 'probability_rows': m}.
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        for stmt in _HEAD_TO_HEAD_DDL:
            conn.execute(stmt)
        conn.commit()
        return _compute_locked(conn, season, on_progress or (lambda _msg: None))
    finally:
        conn.close()


def _compute_locked(
    conn: sqlite3.Connection, season: int, say: Callable[[str], None]
) -> dict[str, int]:
    say(f"compute-stats season={season}: loading roster")
    sample = conn.execute(
        "SELECT standings FROM championship_results WHERE season = ? LIMIT 1", (season,)
    ).fetchone()
    if not sample:
        say(f"  no data for season {season} — nothing to compute")
        return {"drivers": 0, "probability_rows": 0}

    all_drivers = [d.strip() for d in sample["standings"].split(",")]

    max_races = conn.execute(
        "SELECT MAX(num_races) AS m FROM championship_results WHERE season = ?", (season,)
    ).fetchone()["m"]

    say(f"  drivers={len(all_drivers)} max_races={max_races}")

    # Highest position per driver: iterate from longest season down, short-circuit
    # once every driver has claimed a win (position 1 cannot be beaten).
    say("  scanning highest positions")
    driver_stats: dict[str, dict] = {}
    drivers_to_find = set(all_drivers)

    for n in range(max_races, 0, -1):
        if not drivers_to_find:
            break
        rows = conn.execute(
            "SELECT championship_id, standings, num_races FROM championship_results "
            "WHERE num_races = ? AND season = ? ORDER BY championship_id DESC LIMIT 10000",
            (n, season),
        ).fetchall()
        for row in rows:
            cid = row["championship_id"]
            drivers_list = [d.strip() for d in row["standings"].split(",")]
            for position, driver in enumerate(drivers_list, start=1):
                entry = driver_stats.get(driver)
                if entry is None:
                    driver_stats[driver] = {
                        "highest_position": position,
                        "highest_position_max_races": row["num_races"],
                        "highest_position_championship_id": cid,
                        "best_margin": None,
                        "best_margin_championship_id": None,
                        "win_count": 0,
                    }
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif position < entry["highest_position"]:
                    entry["highest_position"] = position
                    entry["highest_position_max_races"] = row["num_races"]
                    entry["highest_position_championship_id"] = cid
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif (
                    position == entry["highest_position"]
                    and row["num_races"] > entry["highest_position_max_races"]
                ):
                    entry["highest_position_max_races"] = row["num_races"]
                    entry["highest_position_championship_id"] = cid

    say("  counting wins")
    for row in conn.execute(
        "SELECT winner, COUNT(*) AS wins FROM championship_results "
        "WHERE winner IS NOT NULL AND season = ? GROUP BY winner",
        (season,),
    ):
        if row["winner"] in driver_stats:
            driver_stats[row["winner"]]["win_count"] = row["wins"]

    say("  best winning margins")
    winners = {d for d, s in driver_stats.items() if s["highest_position"] == 1}
    for row in conn.execute(
        "SELECT winner, points, championship_id FROM championship_results "
        "WHERE winner IS NOT NULL AND season = ?",
        (season,),
    ):
        if row["winner"] not in winners:
            continue
        parts = row["points"].split(",") if row["points"] else []
        if len(parts) < 2:
            continue
        try:
            margin = int(parts[0]) - int(parts[1])
        except ValueError:
            continue
        entry = driver_stats[row["winner"]]
        if entry["best_margin"] is None or margin > entry["best_margin"]:
            entry["best_margin"] = margin
            entry["best_margin_championship_id"] = row["championship_id"]

    say("  writing driver_statistics")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM driver_statistics WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO driver_statistics "
        "(driver_code, season, highest_position, highest_position_max_races, "
        " highest_position_championship_id, best_margin, best_margin_championship_id, win_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                d,
                season,
                s["highest_position"],
                s["highest_position_max_races"],
                s["highest_position_championship_id"],
                s["best_margin"],
                s["best_margin_championship_id"],
                s["win_count"],
            )
            for d, s in driver_stats.items()
        ],
    )
    conn.commit()

    say("  computing win probability cache")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM win_probability_cache WHERE season = ?", (season,))

    totals = {
        row["num_races"]: row["total"]
        for row in conn.execute(
            "SELECT num_races, COUNT(*) AS total FROM championship_results "
            "WHERE season = ? GROUP BY num_races",
            (season,),
        )
    }
    wins_rows = conn.execute(
        "SELECT winner, num_races, COUNT(*) AS wins FROM championship_results "
        "WHERE winner IS NOT NULL AND season = ? GROUP BY winner, num_races",
        (season,),
    ).fetchall()

    seen: set[tuple[str, int]] = set()
    cache_rows: list[tuple] = []
    for row in wins_rows:
        seen.add((row["winner"], row["num_races"]))
        cache_rows.append(
            (row["winner"], row["num_races"], row["wins"], totals.get(row["num_races"], 0), season)
        )
    # Fill zero-win rows so the matrix is dense per (driver, num_races).
    for driver in all_drivers:
        for n, total in totals.items():
            if (driver, n) not in seen:
                cache_rows.append((driver, n, 0, total, season))

    conn.executemany(
        "INSERT INTO win_probability_cache "
        "(driver_code, num_races, win_count, total_at_length, season) VALUES (?, ?, ?, ?, ?)",
        cache_rows,
    )
    conn.commit()

    say("  computing head-to-head + position-distribution caches")
    h2h_pairs, position_rows = _compute_pair_and_position_caches(
        conn, season, all_drivers, say
    )

    say(
        f"  done: {len(driver_stats)} drivers, {len(cache_rows)} probability rows, "
        f"{h2h_pairs} h2h pairs, {position_rows} position rows"
    )
    return {
        "drivers": len(driver_stats),
        "probability_rows": len(cache_rows),
        "head_to_head_pairs": h2h_pairs,
        "position_distribution_rows": position_rows,
    }


def _compute_pair_and_position_caches(
    conn: sqlite3.Connection,
    season: int,
    all_drivers: list[str],
    say: Callable[[str], None],
) -> tuple[int, int]:
    """Single pass over `position_results` populates two caches at once:

    - `driver_head_to_head`: wins/losses per (driver, opponent) — O(C × D²)
      Python all-pairs loop, far cheaper than the SQL self-join which
      materializes C × D × D comparisons even with indexes.
    - `driver_position_distribution`: how often each driver finished P1..PN
      in the season — replaces a `WHERE driver=:d AND season=:s GROUP BY
      position` scan over `position_results` (16M+ rows) with a PK lookup.
    """
    pair_wins: dict[tuple[str, str], int] = {}
    position_counts: dict[tuple[str, int], int] = {}

    cursor = conn.execute(
        "SELECT championship_id, driver_code, position FROM position_results "
        "WHERE season = ? ORDER BY championship_id",
        (season,),
    )
    current_cid: int | None = None
    placements: list[tuple[str, int]] = []
    seen_count = 0

    def flush(group: list[tuple[str, int]]) -> None:
        # All-pairs: each driver beats every driver behind them.
        n = len(group)
        for i in range(n):
            di, pi = group[i]
            for j in range(i + 1, n):
                dj, pj = group[j]
                if pi < pj:
                    pair_wins[(di, dj)] = pair_wins.get((di, dj), 0) + 1
                elif pj < pi:
                    pair_wins[(dj, di)] = pair_wins.get((dj, di), 0) + 1

    for row in cursor:
        cid = row["championship_id"]
        if cid != current_cid:
            if placements:
                flush(placements)
                seen_count += 1
                if seen_count % 100_000 == 0:
                    say(f"    processed {seen_count} championships")
            current_cid = cid
            placements = []
        d, p = row["driver_code"], row["position"]
        placements.append((d, p))
        position_counts[(d, p)] = position_counts.get((d, p), 0) + 1
    if placements:
        flush(placements)

    say(f"    aggregated {seen_count + (1 if placements else 0)} championships")

    # Materialize head-to-head rows: (driver, opponent, wins, losses).
    h2h_rows: list[tuple] = []
    for d in all_drivers:
        for opp in all_drivers:
            if d == opp:
                continue
            wins = pair_wins.get((d, opp), 0)
            losses = pair_wins.get((opp, d), 0)
            h2h_rows.append((season, d, opp, wins, losses))

    # Materialize position-distribution rows.
    position_rows: list[tuple] = [
        (season, driver, position, count)
        for (driver, position), count in position_counts.items()
    ]

    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM driver_head_to_head WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO driver_head_to_head (season, driver_code, opponent, wins, losses) "
        "VALUES (?, ?, ?, ?, ?)",
        h2h_rows,
    )
    conn.execute("DELETE FROM driver_position_distribution WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO driver_position_distribution (season, driver_code, position, count) "
        "VALUES (?, ?, ?, ?)",
        position_rows,
    )
    conn.commit()
    return len(h2h_rows), len(position_rows)
