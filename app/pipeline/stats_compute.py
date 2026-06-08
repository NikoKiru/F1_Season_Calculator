"""Pre-compute driver_statistics and win_probability_cache for a season.

These tables turn the three expensive aggregations (highest position, best
margin, win-probability-by-length) into O(1) lookups for the API layer.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from pathlib import Path

import numpy as np

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
    """
    CREATE TABLE IF NOT EXISTS notable_scenarios (
        season INTEGER NOT NULL,
        category TEXT NOT NULL,
        championship_id INTEGER,
        metric_value INTEGER,
        detail TEXT,
        PRIMARY KEY (season, category)
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

    notable = _compute_notable_scenarios(
        conn, season, all_drivers, max_races, driver_stats, say
    )

    say(
        f"  done: {len(driver_stats)} drivers, {len(cache_rows)} probability rows, "
        f"{h2h_pairs} h2h pairs, {position_rows} position rows, "
        f"{notable} notable scenarios"
    )
    return {
        "drivers": len(driver_stats),
        "probability_rows": len(cache_rows),
        "head_to_head_pairs": h2h_pairs,
        "position_distribution_rows": position_rows,
        "notable_scenarios": notable,
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


def _cid_for_mask(
    conn: sqlite3.Connection, season: int, mask: int, round_order: list[int]
) -> int | None:
    """Resolve a weekend-bitmask back to its championship_id via the `rounds`
    string the writer stored (ascending round order, matching `round_order`)."""
    rounds_csv = ",".join(
        str(round_order[i]) for i in range(len(round_order)) if mask & (1 << i)
    )
    row = conn.execute(
        "SELECT championship_id FROM championship_results "
        "WHERE season = ? AND rounds = ?",
        (season, rounds_csv),
    ).fetchone()
    return int(row["championship_id"]) if row else None


def _compute_notable_scenarios(
    conn: sqlite3.Connection,
    season: int,
    all_drivers: list[str],
    max_races: int,
    driver_stats: dict[str, dict],
    say: Callable[[str], None],
) -> int:
    """Mine the enumerated championships for the most extreme/interesting
    scenarios and store one pointer row per category in `notable_scenarios`.

    Categories: nail_biter (smallest winning margin), demolition (largest
    margin), against_all_odds (most rounds counted while crowning someone other
    than the real season champion), cinderella (rarest champion), and kingmaker
    (the round that flips the title in the most `(S, S+round)` pairs).

    Cost: one O(C) scan over `championship_results` plus an O(N) vectorised
    round-pairing pass over a bitmask-indexed winner array.
    """
    say("  mining notable scenarios")

    # The single full-length scenario gives both the real champion and the
    # weekend-index -> round-number ordering used to bitmask every subset.
    full = conn.execute(
        "SELECT rounds, winner FROM championship_results "
        "WHERE season = ? AND num_races = ? LIMIT 1",
        (season, max_races),
    ).fetchone()
    if full is None:
        say("    no full-length scenario — skipping")
        return 0
    round_order = [int(r) for r in full["rounds"].split(",")]
    index_of_round = {r: i for i, r in enumerate(round_order)}
    real_champion = full["winner"]
    n_weekends = len(round_order)

    driver_idx = {d: i for i, d in enumerate(all_drivers)}
    winners_by_mask = np.full(1 << n_weekends, -1, dtype=np.int32)

    nail: tuple[int, int, int] | None = None   # (margin, num_races, cid) -> minimise
    demo: tuple[int, int, int] | None = None   # (margin, num_races, cid) -> maximise
    upset: tuple[int, int] | None = None       # (num_races, cid) for winner != real

    for row in conn.execute(
        "SELECT championship_id, num_races, rounds, winner, points "
        "FROM championship_results WHERE season = ? ORDER BY championship_id",
        (season,),
    ):
        cid = row["championship_id"]
        nr = row["num_races"]

        mask = 0
        for r in row["rounds"].split(","):
            mask |= 1 << index_of_round[int(r)]
        winners_by_mask[mask] = driver_idx.get(row["winner"], -1)

        parts = row["points"].split(",") if row["points"] else []
        if len(parts) >= 2:
            try:
                margin = int(parts[0]) - int(parts[1])
            except ValueError:
                margin = None
            if margin is not None:
                # Smallest margin; tie-break most races, then lowest cid (scan
                # is id-ordered, so the first row at a tie already has lowest id).
                if nail is None or (margin, -nr) < (nail[0], -nail[1]):
                    nail = (margin, nr, cid)
                # Largest margin; same tie-break.
                if demo is None or (margin, nr) > (demo[0], demo[1]):
                    demo = (margin, nr, cid)

        if row["winner"] != real_champion and (upset is None or nr > upset[0]):
            upset = (nr, cid)

    rows: list[tuple] = []
    if nail is not None:
        rows.append((season, "nail_biter", nail[2], nail[0], None))
    if demo is not None:
        rows.append((season, "demolition", demo[2], demo[0], None))
    if upset is not None:
        rows.append((
            season, "against_all_odds", upset[1], upset[0],
            json.dumps({"real_champion": real_champion}),
        ))

    # Cinderella: rarest champion (fewest titles, >= 1). Tie-break: most
    # dramatic single win (largest best margin), then alphabetical code.
    champions = sorted(
        (s["win_count"], -(s["best_margin"] or 0), d)
        for d, s in driver_stats.items()
        if s["win_count"] >= 1 and s["best_margin_championship_id"] is not None
    )
    if champions:
        win_count, _, code = champions[0]
        rows.append((
            season, "cinderella",
            driver_stats[code]["best_margin_championship_id"],
            win_count, json.dumps({"driver_code": code}),
        ))

    # Kingmaker: the round that flips the champion in the most (S, S+round)
    # pairs. One vectorised comparison per weekend over the bitmask array.
    if n_weekends >= 2:
        all_masks = np.arange(1 << n_weekends)
        best_round_idx, best_flips = -1, -1
        for bit_i in range(n_weekends):
            bit = 1 << bit_i
            without = all_masks[(all_masks & bit) == 0]
            without = without[without != 0]            # drop the empty set
            flips = int(np.count_nonzero(
                winners_by_mask[without] != winners_by_mask[without | bit]
            ))
            if flips > best_flips:                     # ties keep the lowest round
                best_round_idx, best_flips = bit_i, flips

        if best_flips > 0:
            bit = 1 << best_round_idx
            without = all_masks[(all_masks & bit) == 0]
            without = without[without != 0]
            flip_befores = without[
                winners_by_mask[without] != winners_by_mask[without | bit]
            ]
            # Representative = the biggest 'before' scenario that flips.
            popcount = np.array([int(m).bit_count() for m in flip_befores])
            order = np.lexsort((flip_befores, -popcount))
            before_mask = int(flip_befores[order[0]])
            before_cid = _cid_for_mask(conn, season, before_mask, round_order)
            after_cid = _cid_for_mask(conn, season, before_mask | bit, round_order)
            rows.append((
                season, "kingmaker", after_cid, best_flips,
                json.dumps({
                    "round": round_order[best_round_idx],
                    "before_cid": before_cid,
                }),
            ))

    conn.execute("BEGIN IMMEDIATE")
    conn.execute("DELETE FROM notable_scenarios WHERE season = ?", (season,))
    conn.executemany(
        "INSERT INTO notable_scenarios "
        "(season, category, championship_id, metric_value, detail) "
        "VALUES (?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()
    say(f"    wrote {len(rows)} notable scenarios")
    return len(rows)
