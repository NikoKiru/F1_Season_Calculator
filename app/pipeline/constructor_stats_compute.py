"""Pre-compute constructor_statistics + constructor_win_probability_cache.

Mirror of `app/pipeline/stats_compute.py` — same six sub-computations
(highest position, win count, best margin, win-probability cache,
head-to-head, position distribution) targeting the constructor tables.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

# Lazy DDL for the head-to-head + position-distribution caches. Running the
# full SCHEMA_STATEMENTS would force CREATE INDEX IF NOT EXISTS on
# constructor_position_results, which is a full-table scan if an index is
# missing. CREATE on an empty new table and its index is instant.
_HEAD_TO_HEAD_DDL = (
    """
    CREATE TABLE IF NOT EXISTS constructor_head_to_head (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        opponent TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (season, constructor_name, opponent)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_constructor_h2h_season "
    "ON constructor_head_to_head (season, constructor_name)",
    """
    CREATE TABLE IF NOT EXISTS constructor_position_distribution (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        position INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (season, constructor_name, position)
    )
    """,
)


def compute(
    db_path: Path,
    season: int,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Populate constructor_statistics + constructor_win_probability_cache."""
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
    say(f"compute-constructor-stats season={season}: loading roster")
    sample = conn.execute(
        "SELECT standings FROM constructor_championship_results "
        "WHERE season = ? LIMIT 1",
        (season,),
    ).fetchone()
    if not sample:
        say(f"  no data for season {season} — nothing to compute")
        return {"constructors": 0, "probability_rows": 0}

    all_constructors = [c.strip() for c in sample["standings"].split(",")]

    max_races = conn.execute(
        "SELECT MAX(num_races) AS m FROM constructor_championship_results "
        "WHERE season = ?",
        (season,),
    ).fetchone()["m"]

    say(f"  constructors={len(all_constructors)} max_races={max_races}")

    say("  scanning highest positions")
    constructor_stats: dict[str, dict] = {}
    constructors_to_find = set(all_constructors)

    for n in range(max_races, 0, -1):
        if not constructors_to_find:
            break
        rows = conn.execute(
            "SELECT championship_id, standings, num_races "
            "FROM constructor_championship_results "
            "WHERE num_races = ? AND season = ? "
            "ORDER BY championship_id DESC LIMIT 10000",
            (n, season),
        ).fetchall()
        for row in rows:
            cid = row["championship_id"]
            order = [c.strip() for c in row["standings"].split(",")]
            for position, constructor in enumerate(order, start=1):
                entry = constructor_stats.get(constructor)
                if entry is None:
                    constructor_stats[constructor] = {
                        "highest_position": position,
                        "highest_position_max_races": row["num_races"],
                        "highest_position_championship_id": cid,
                        "best_margin": None,
                        "best_margin_championship_id": None,
                        "win_count": 0,
                    }
                    if position == 1:
                        constructors_to_find.discard(constructor)
                elif position < entry["highest_position"]:
                    entry["highest_position"] = position
                    entry["highest_position_max_races"] = row["num_races"]
                    entry["highest_position_championship_id"] = cid
                    if position == 1:
                        constructors_to_find.discard(constructor)
                elif (
                    position == entry["highest_position"]
                    and row["num_races"] > entry["highest_position_max_races"]
                ):
                    entry["highest_position_max_races"] = row["num_races"]
                    entry["highest_position_championship_id"] = cid

    say("  counting wins")
    for row in conn.execute(
        "SELECT winner, COUNT(*) AS wins FROM constructor_championship_results "
        "WHERE winner IS NOT NULL AND season = ? GROUP BY winner",
        (season,),
    ):
        if row["winner"] in constructor_stats:
            constructor_stats[row["winner"]]["win_count"] = row["wins"]

    say("  best winning margins")
    winners = {c for c, s in constructor_stats.items() if s["highest_position"] == 1}
    for row in conn.execute(
        "SELECT winner, points, championship_id "
        "FROM constructor_championship_results "
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
        entry = constructor_stats[row["winner"]]
        if entry["best_margin"] is None or margin > entry["best_margin"]:
            entry["best_margin"] = margin
            entry["best_margin_championship_id"] = row["championship_id"]

    say("  writing constructor_statistics")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM constructor_statistics WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO constructor_statistics "
        "(constructor_name, season, highest_position, highest_position_max_races, "
        " highest_position_championship_id, best_margin, "
        " best_margin_championship_id, win_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [
            (
                c,
                season,
                s["highest_position"],
                s["highest_position_max_races"],
                s["highest_position_championship_id"],
                s["best_margin"],
                s["best_margin_championship_id"],
                s["win_count"],
            )
            for c, s in constructor_stats.items()
        ],
    )
    conn.commit()

    say("  computing win probability cache")
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "DELETE FROM constructor_win_probability_cache WHERE season = ?", (season,)
    )

    totals = {
        row["num_races"]: row["total"]
        for row in conn.execute(
            "SELECT num_races, COUNT(*) AS total FROM constructor_championship_results "
            "WHERE season = ? GROUP BY num_races",
            (season,),
        )
    }
    wins_rows = conn.execute(
        "SELECT winner, num_races, COUNT(*) AS wins "
        "FROM constructor_championship_results "
        "WHERE winner IS NOT NULL AND season = ? GROUP BY winner, num_races",
        (season,),
    ).fetchall()

    seen: set[tuple[str, int]] = set()
    cache_rows: list[tuple] = []
    for row in wins_rows:
        seen.add((row["winner"], row["num_races"]))
        cache_rows.append(
            (
                row["winner"],
                row["num_races"],
                row["wins"],
                totals.get(row["num_races"], 0),
                season,
            )
        )
    # Fill zero-win rows so the matrix is dense per (constructor, num_races).
    for constructor in all_constructors:
        for n, total in totals.items():
            if (constructor, n) not in seen:
                cache_rows.append((constructor, n, 0, total, season))

    conn.executemany(
        "INSERT INTO constructor_win_probability_cache "
        "(constructor_name, num_races, win_count, total_at_length, season) "
        "VALUES (?, ?, ?, ?, ?)",
        cache_rows,
    )
    conn.commit()

    say("  computing head-to-head + position-distribution caches")
    h2h_pairs, position_rows = _compute_pair_and_position_caches(
        conn, season, all_constructors, say
    )

    say(
        f"  done: {len(constructor_stats)} constructors, "
        f"{len(cache_rows)} probability rows, "
        f"{h2h_pairs} h2h pairs, {position_rows} position rows"
    )
    return {
        "constructors": len(constructor_stats),
        "probability_rows": len(cache_rows),
        "head_to_head_pairs": h2h_pairs,
        "position_distribution_rows": position_rows,
    }


def _compute_pair_and_position_caches(
    conn: sqlite3.Connection,
    season: int,
    all_constructors: list[str],
    say: Callable[[str], None],
) -> tuple[int, int]:
    pair_wins: dict[tuple[str, str], int] = {}
    position_counts: dict[tuple[str, int], int] = {}

    cursor = conn.execute(
        "SELECT championship_id, constructor_name, position "
        "FROM constructor_position_results "
        "WHERE season = ? ORDER BY championship_id",
        (season,),
    )
    current_cid: int | None = None
    placements: list[tuple[str, int]] = []
    seen_count = 0

    def flush(group: list[tuple[str, int]]) -> None:
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
        c, p = row["constructor_name"], row["position"]
        placements.append((c, p))
        position_counts[(c, p)] = position_counts.get((c, p), 0) + 1
    if placements:
        flush(placements)

    say(f"    aggregated {seen_count + (1 if placements else 0)} championships")

    h2h_rows: list[tuple] = []
    for c in all_constructors:
        for opp in all_constructors:
            if c == opp:
                continue
            wins = pair_wins.get((c, opp), 0)
            losses = pair_wins.get((opp, c), 0)
            h2h_rows.append((season, c, opp, wins, losses))

    position_rows: list[tuple] = [
        (season, constructor, position, count)
        for (constructor, position), count in position_counts.items()
    ]

    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM constructor_head_to_head WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO constructor_head_to_head "
        "(season, constructor_name, opponent, wins, losses) "
        "VALUES (?, ?, ?, ?, ?)",
        h2h_rows,
    )
    conn.execute(
        "DELETE FROM constructor_position_distribution WHERE season = ?", (season,)
    )
    conn.executemany(
        "INSERT INTO constructor_position_distribution "
        "(season, constructor_name, position, count) VALUES (?, ?, ?, ?)",
        position_rows,
    )
    conn.commit()
    return len(h2h_rows), len(position_rows)
