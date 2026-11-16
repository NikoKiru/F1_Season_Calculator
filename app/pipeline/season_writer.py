"""Write every scenario of one season, for drivers or constructors.

Uses stdlib sqlite3 directly: the pipeline is a CLI-only operation and takes
the connection for itself.

Three things keep the 2^N - 1 scenarios affordable:

- Subsets are ranked a batch at a time (`combinator.rank_batch`), not one by
  one in Python.
- Position rows, one per entry per scenario and so the bulk of the data, are
  never built in Python. SQLite derives them from the standings text it was
  just handed.
- The tables carry no index beyond the ones `schema.py` explains.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from itertools import repeat
from pathlib import Path

import numpy as np

from app.pipeline.combinator import rank_batch, subset_batches, total_combinations
from app.pipeline.tables import SeasonTables


def _tune_for_bulk_load(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")


def _restore_safe(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA synchronous=NORMAL")


def _insert_results_sql(tables: SeasonTables) -> str:
    # championship_id is set explicitly: the table is AUTOINCREMENT, and after
    # a clear_season + reprocess cycle sqlite_sequence keeps counting from the
    # old maximum, so auto-assigned ids would drift from the ids the position
    # rows are given.
    return (
        f"INSERT INTO {tables.results} "
        "(championship_id, season, num_races, rounds, standings, winner, points) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)"
    )


def _insert_positions_sql(tables: SeasonTables) -> str:
    """One row per place in each stored standings, for a range of scenario ids.

    The standings text becomes a JSON array ('A,B' -> '["A","B"]') and
    json_each hands back each name with its index. Backslashes and quotes are
    escaped first so any name survives the trip.
    """
    as_json = (
        "'[\"' || replace(replace(replace(cr.standings, "
        "'\\', '\\\\'), '\"', '\\\"'), ',', '\",\"') || '\"]'"
    )
    return (
        f"INSERT INTO {tables.positions} (season, {tables.entry}, position, championship_id) "
        f"SELECT cr.season, place.value, place.key + 1, cr.championship_id "
        f"FROM {tables.results} cr, json_each({as_json}) place "
        "WHERE cr.championship_id BETWEEN ? AND ?"
    )


def write_season(
    db_path: Path,
    tables: SeasonTables,
    labels: np.ndarray,
    scores: np.ndarray,
    countback: np.ndarray,
    round_numbers: np.ndarray,
    season: int,
    batch_size: int = 100_000,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Generate + insert every weekend combination for one season.

    `labels` names the entries (driver codes or team names), `scores` and
    `countback` are (entries, weekends). Returns the scenario count.
    """
    num_weekends = scores.shape[1]
    if len(labels) == 0 or num_weekends == 0:
        return 0
    total = total_combinations(num_weekends)
    names = [str(label) for label in labels.tolist()]
    name_at = names.__getitem__
    round_at = [str(number) for number in round_numbers.tolist()].__getitem__
    insert_results = _insert_results_sql(tables)
    insert_positions = _insert_positions_sql(tables)

    conn = sqlite3.connect(db_path)
    try:
        _tune_for_bulk_load(conn)
        conn.execute("BEGIN IMMEDIATE")

        next_id = (
            conn.execute(
                f"SELECT COALESCE(MAX(championship_id), 0) FROM {tables.results}"
            ).fetchone()[0]
            + 1
        )
        inserted = 0

        # Ids follow subset order, and subsets run shortest first. The position
        # lists rely on that: a higher id is never a shorter scenario.
        for subsets in subset_batches(num_weekends, batch_size):
            order, points = rank_batch(scores, countback, subsets)
            count, length = subsets.shape
            order_rows = order.tolist()
            last_id = next_id + count - 1

            conn.executemany(
                insert_results,
                zip(
                    range(next_id, last_id + 1),
                    repeat(season),
                    repeat(length),
                    [",".join(map(round_at, subset)) for subset in subsets.tolist()],
                    [",".join(map(name_at, row)) for row in order_rows],
                    [names[row[0]] for row in order_rows],
                    [",".join(map(str, row)) for row in points.tolist()],
                ),
            )
            conn.execute(insert_positions, (next_id, last_id))

            next_id = last_id + 1
            inserted += count
            if on_progress:
                on_progress(inserted, total)

        conn.commit()
        _restore_safe(conn)
        return inserted
    finally:
        conn.close()


def clear_season(db_path: Path, tables: SeasonTables, season: int) -> None:
    """Remove a season's scenarios and everything computed from them, and the
    build stamp with them. Used before a reprocess."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM season_builds WHERE season = ?", (season,))
        for table in tables.derived:
            conn.execute(f"DELETE FROM {table} WHERE season = ?", (season,))
        conn.commit()
    finally:
        conn.close()
