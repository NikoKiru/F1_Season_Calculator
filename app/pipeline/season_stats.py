"""Pre-compute a season's statistics tables, for drivers or constructors.

One pass over the season's scenarios fills the tables that turn the expensive
aggregations into lookups for the API layer: best finish and biggest winning
margin per entry, wins per season length, head-to-head records, how often each
entry finishes in each position, and (for drivers) the notable scenarios.

The pass reads the result table a chunk at a time and does its counting in
numpy. A Python loop per scenario, or per pair of entries per scenario, is
what made this step slower than writing the scenarios in the first place.
"""
from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import numpy as np

from app.pipeline.tables import SeasonTables

CHUNK_ROWS = 50_000
_PAIR_BLOCK = 8_192  # rows compared at once for head-to-head: rows x entries^2 flags


def compute(
    db_path: Path,
    tables: SeasonTables,
    season: int,
    *,
    noun: str,
    ddl: Sequence[str] = (),
    notable: bool = False,
    on_progress: Callable[[str], None] | None = None,
) -> dict[str, int]:
    """Fill the statistics tables of `tables` for `season`.

    `noun` names the entries in messages and in the summary dict ("drivers",
    "constructors"). `ddl` creates the cache tables this side writes to.
    """
    conn = sqlite3.connect(db_path)
    try:
        for statement in ddl:
            conn.execute(statement)
        conn.commit()
        return _compute(conn, tables, season, noun, notable, on_progress or (lambda _: None))
    finally:
        conn.close()


def _compute(
    conn: sqlite3.Connection,
    tables: SeasonTables,
    season: int,
    noun: str,
    notable: bool,
    say: Callable[[str], None],
) -> dict[str, int]:
    say(f"compute stats for {noun}, season={season}: loading roster")
    sample = conn.execute(
        f"SELECT standings FROM {tables.results} WHERE season = ? LIMIT 1", (season,)
    ).fetchone()
    if not sample:
        say(f"  no data for season {season} — nothing to compute")
        return {noun: 0, "probability_rows": 0}

    # Every scenario ranks every entry, so one row names them all.
    entries: list[str] = sample[0].split(",")
    index_of = {name: i for i, name in enumerate(entries)}
    n = len(entries)
    first_id, last_id, max_races = conn.execute(
        f"SELECT MIN(championship_id), MAX(championship_id), MAX(num_races) "
        f"FROM {tables.results} WHERE season = ?",
        (season,),
    ).fetchone()
    say(f"  {noun}={n} max_races={max_races}")

    # The single full-length scenario: the real champion, and the order of the
    # weekends, which gives every subset a bitmask.
    full_rounds, real_champion = conn.execute(
        f"SELECT rounds, winner FROM {tables.results} "
        "WHERE season = ? AND num_races = ? LIMIT 1",
        (season, max_races),
    ).fetchone()
    round_order = [int(r) for r in full_rounds.split(",")]
    bit_of_round = {str(r): 1 << i for i, r in enumerate(round_order)}
    real_index = index_of.get(real_champion, -1)

    span = max_races + 1  # room for one season length inside a combined sort key
    best_position = np.full(n, n, dtype=np.int64)  # 0-based; n means not seen yet
    best_position_races = np.zeros(n, dtype=np.int64)
    best_position_id = np.zeros(n, dtype=np.int64)
    best_margin = np.full(n, -1, dtype=np.int64)  # -1 means never won
    best_margin_id = np.zeros(n, dtype=np.int64)
    wins = np.zeros((span, n), dtype=np.int64)  # [season length, entry]
    scenarios = np.zeros(span, dtype=np.int64)  # per season length
    finishes = np.zeros((n, n), dtype=np.int64)  # [entry, position]
    ahead = np.zeros((n, n), dtype=np.int64)  # [a, b]: scenarios with a ahead of b

    winner_by_mask = (
        np.full(1 << len(round_order), -1, dtype=np.int32) if notable else None
    )
    closest: tuple[int, int, int] | None = None  # (margin, races, id), smallest margin
    widest: tuple[int, int, int] | None = None  # (margin, races, id), largest margin
    upset: tuple[int, int] | None = None  # (races, id): longest with another champion

    say("  scanning every scenario")
    # A lone entry has no runner-up, so no margin; the expression still parses.
    cursor = conn.execute(
        "SELECT championship_id, num_races, rounds, standings, "
        "       CAST(points AS INTEGER) "
        "       - CAST(substr(points, instr(points, ',') + 1) AS INTEGER) "
        f"FROM {tables.results} "
        "WHERE championship_id BETWEEN ? AND ? AND season = ? "
        "ORDER BY championship_id",
        (first_id, last_id, season),
    )
    seen = 0
    places = np.arange(n)
    while rows := cursor.fetchmany(CHUNK_ROWS):
        ids_col, races_col, rounds_col, standings_col, margin_col = zip(*rows, strict=True)
        count = len(rows)
        ids = np.array(ids_col, dtype=np.int64)
        races = np.array(races_col, dtype=np.int64)
        margins = np.array(margin_col, dtype=np.int64)
        # order[i, p]: the entry in place p of scenario i. Ids ascend, so the
        # first row to reach a value is also the one with the lowest id.
        order = np.fromiter(
            map(index_of.__getitem__, ",".join(standings_col).split(",")),
            dtype=np.int64,
            count=count * n,
        ).reshape(count, n)
        winners = order[:, 0]

        wins += np.bincount(races * n + winners, minlength=span * n).reshape(span, n)
        scenarios += np.bincount(races, minlength=span)
        finishes += np.bincount((order * n + places).ravel(), minlength=n * n).reshape(n, n)

        # position[i, e]: where entry e finished in scenario i.
        position = np.empty((count, n), dtype=np.int16)
        np.put_along_axis(position, order, places.astype(np.int16)[None, :], axis=1)
        for start in range(0, count, _PAIR_BLOCK):
            block = position[start : start + _PAIR_BLOCK]
            ahead += (block[:, :, None] < block[:, None, :]).sum(axis=0)

        # Best finish: lowest position, then the longest scenario, then the
        # lowest id. argmin returns the first row of the smallest key.
        key = position.astype(np.int64) * span + (max_races - races)[:, None]
        rows_at_best = key.argmin(axis=0)
        chunk_position = position[rows_at_best, places].astype(np.int64)
        chunk_races = races[rows_at_best]
        better = (chunk_position < best_position) | (
            (chunk_position == best_position) & (chunk_races > best_position_races)
        )
        best_position[better] = chunk_position[better]
        best_position_races[better] = chunk_races[better]
        best_position_id[better] = ids[rows_at_best][better]

        if n >= 2:
            for winner in np.unique(winners).tolist():
                won = np.flatnonzero(winners == winner)
                row = won[margins[won].argmax()]
                if margins[row] > best_margin[winner]:
                    best_margin[winner] = margins[row]
                    best_margin_id[winner] = ids[row]

        if winner_by_mask is not None:
            bits = np.fromiter(
                map(bit_of_round.__getitem__, ",".join(rounds_col).split(",")),
                dtype=np.int64,
                count=int(races.sum()),
            )
            masks = np.add.reduceat(bits, np.cumsum(races) - races)
            winner_by_mask[masks] = winners

            if n >= 2:
                # Closest: smallest margin, then most races, then lowest id.
                row = int((margins * span + (max_races - races)).argmin())
                found = (int(margins[row]), int(races[row]), int(ids[row]))
                if closest is None or (found[0], -found[1]) < (closest[0], -closest[1]):
                    closest = found
                # Widest: largest margin, same tie-breaks.
                row = int((margins * span + races).argmax())
                found = (int(margins[row]), int(races[row]), int(ids[row]))
                if widest is None or found[:2] > widest[:2]:
                    widest = found
            others = np.flatnonzero(winners != real_index)
            if others.size:
                row = others[races[others].argmax()]
                if upset is None or races[row] > upset[0]:
                    upset = (int(races[row]), int(ids[row]))

        seen += count
        if seen % 500_000 < count:
            say(f"    processed {seen:,} scenarios")
    say(f"    aggregated {seen:,} scenarios")

    statistics_rows = [
        (
            name,
            season,
            int(best_position[i]) + 1,
            int(best_position_races[i]),
            int(best_position_id[i]),
            int(best_margin[i]) if best_margin[i] >= 0 else None,
            int(best_margin_id[i]) if best_margin[i] >= 0 else None,
            int(wins[:, i].sum()),
        )
        for i, name in enumerate(entries)
    ]
    lengths = np.flatnonzero(scenarios).tolist()
    probability_rows = [
        (name, length, int(wins[length, i]), int(scenarios[length]), season)
        for i, name in enumerate(entries)
        for length in lengths
    ]
    head_to_head_rows = [
        (season, name, opponent, int(ahead[i, j]), int(ahead[j, i]))
        for i, name in enumerate(entries)
        for j, opponent in enumerate(entries)
        if i != j
    ]
    distribution_rows = [
        (season, name, place + 1, int(finishes[i, place]))
        for i, name in enumerate(entries)
        for place in range(n)
        if finishes[i, place]
    ]

    say("  writing statistics, win probability, head-to-head and position caches")
    entry = tables.entry
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(f"DELETE FROM {tables.statistics} WHERE season = ?", (season,))
    conn.executemany(
        f"INSERT INTO {tables.statistics} "
        f"({entry}, season, highest_position, highest_position_max_races, "
        " highest_position_championship_id, best_margin, best_margin_championship_id, "
        " win_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        statistics_rows,
    )
    conn.execute(f"DELETE FROM {tables.win_probability} WHERE season = ?", (season,))
    conn.executemany(
        f"INSERT INTO {tables.win_probability} "
        f"({entry}, num_races, win_count, total_at_length, season) VALUES (?, ?, ?, ?, ?)",
        probability_rows,
    )
    conn.execute(f"DELETE FROM {tables.head_to_head} WHERE season = ?", (season,))
    conn.executemany(
        f"INSERT INTO {tables.head_to_head} (season, {entry}, opponent, wins, losses) "
        "VALUES (?, ?, ?, ?, ?)",
        head_to_head_rows,
    )
    conn.execute(f"DELETE FROM {tables.position_distribution} WHERE season = ?", (season,))
    conn.executemany(
        f"INSERT INTO {tables.position_distribution} (season, {entry}, position, count) "
        "VALUES (?, ?, ?, ?)",
        distribution_rows,
    )
    conn.commit()

    summary = {
        noun: len(entries),
        "probability_rows": len(probability_rows),
        "head_to_head_pairs": len(head_to_head_rows),
        "position_distribution_rows": len(distribution_rows),
    }
    if winner_by_mask is not None:
        summary["notable_scenarios"] = _write_notable_scenarios(
            conn,
            tables,
            season,
            entries=entries,
            round_order=round_order,
            real_champion=real_champion,
            statistics_rows=statistics_rows,
            winner_by_mask=winner_by_mask,
            closest=closest,
            widest=widest,
            upset=upset,
            say=say,
        )
    say("  done: " + ", ".join(f"{value} {key}" for key, value in summary.items()))
    return summary


def _popcount(masks: np.ndarray, bits: int) -> np.ndarray:
    count = np.zeros(masks.shape, dtype=np.int64)
    for bit in range(bits):
        count += (masks >> bit) & 1
    return count


def _id_for_mask(
    conn: sqlite3.Connection,
    tables: SeasonTables,
    season: int,
    mask: int,
    round_order: list[int],
) -> int | None:
    """Resolve a weekend bitmask back to its championship_id via the `rounds`
    text the writer stored. `+season` keeps the lookup on the rounds index."""
    rounds_csv = ",".join(
        str(round_order[i]) for i in range(len(round_order)) if mask & (1 << i)
    )
    row = conn.execute(
        f"SELECT championship_id FROM {tables.results} WHERE rounds = ? AND +season = ?",
        (rounds_csv, season),
    ).fetchone()
    return int(row[0]) if row else None


def _write_notable_scenarios(
    conn: sqlite3.Connection,
    tables: SeasonTables,
    season: int,
    *,
    entries: list[str],
    round_order: list[int],
    real_champion: str,
    statistics_rows: list[tuple[Any, ...]],
    winner_by_mask: np.ndarray,
    closest: tuple[int, int, int] | None,
    widest: tuple[int, int, int] | None,
    upset: tuple[int, int] | None,
    say: Callable[[str], None],
) -> int:
    """Store one pointer row per category in `notable_scenarios`.

    Categories: nail_biter (smallest winning margin), demolition (largest
    margin), against_all_odds (most rounds counted while crowning someone other
    than the real season champion), cinderella (rarest champion), and kingmaker
    (the round that flips the title in the most `(S, S+round)` pairs).
    """
    say("  mining notable scenarios")
    rows: list[tuple[Any, ...]] = []
    if closest is not None:
        rows.append((season, "nail_biter", closest[2], closest[0], None))
    if widest is not None:
        rows.append((season, "demolition", widest[2], widest[0], None))
    if upset is not None:
        rows.append((
            season, "against_all_odds", upset[1], upset[0],
            json.dumps({"real_champion": real_champion}),
        ))

    # Cinderella: rarest champion (fewest titles, >= 1). Tie-break: most
    # dramatic single win (largest best margin), then alphabetical code.
    champions = sorted(
        (win_count, -(margin or 0), name, margin_id)
        for name, _, _, _, _, margin, margin_id, win_count in statistics_rows
        if win_count >= 1 and margin_id is not None
    )
    if champions:
        win_count, _, name, margin_id = champions[0]
        rows.append((
            season, "cinderella", margin_id, win_count, json.dumps({"driver_code": name}),
        ))

    # Kingmaker: the round that flips the champion in the most (S, S+round)
    # pairs. One vectorised comparison per weekend over the bitmask array.
    weekends = len(round_order)
    if weekends >= 2:
        all_masks = np.arange(1, 1 << weekends)  # every non-empty subset
        best_bit, best_flips = -1, -1
        for bit_index in range(weekends):
            bit = 1 << bit_index
            without = all_masks[(all_masks & bit) == 0]
            flips = int(np.count_nonzero(
                winner_by_mask[without] != winner_by_mask[without | bit]
            ))
            if flips > best_flips:  # ties keep the lowest round
                best_bit, best_flips = bit_index, flips

        if best_flips > 0:
            bit = 1 << best_bit
            without = all_masks[(all_masks & bit) == 0]
            flipped = without[winner_by_mask[without] != winner_by_mask[without | bit]]
            # Representative = the biggest 'before' scenario that flips.
            pick = np.lexsort((flipped, -_popcount(flipped, weekends)))[0]
            before_mask = int(flipped[pick])
            before_id = _id_for_mask(conn, tables, season, before_mask, round_order)
            after_id = _id_for_mask(conn, tables, season, before_mask | bit, round_order)
            rows.append((
                season, "kingmaker", after_id, best_flips,
                json.dumps({"round": round_order[best_bit], "before_cid": before_id}),
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
