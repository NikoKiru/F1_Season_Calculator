"""Batch-insert generated championships into SQLite.

Uses stdlib sqlite3 directly (not SQLAlchemy) to avoid per-row ORM overhead
during the 2^N-1 insert path — the pipeline is a CLI-only operation and can
safely take over the connection exclusively.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Callable, Iterable

import numpy as np

from app.pipeline.combinator import rank_standings, race_combinations, total_combinations


INSERT_CHAMPIONSHIP = (
    "INSERT INTO championship_results (season, num_races, rounds, standings, winner, points) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)
INSERT_POSITION = (
    "INSERT INTO position_results (championship_id, driver_code, position, points, season) "
    "VALUES (?, ?, ?, ?, ?)"
)


def _tune_for_bulk_load(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("PRAGMA temp_store=MEMORY")
    conn.execute("PRAGMA cache_size=-200000")


def _restore_safe(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA synchronous=NORMAL")


def process_season(
    db_path: Path,
    drivers: np.ndarray,
    scores: np.ndarray,
    season: int,
    batch_size: int = 100_000,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    """Generate + insert every combination for one season. Returns row count."""
    num_races = scores.shape[1]
    total = total_combinations(num_races)

    conn = sqlite3.connect(db_path)
    try:
        _tune_for_bulk_load(conn)
        # One transaction covers the entire load — commit at the very end
        conn.execute("BEGIN IMMEDIATE")

        # Start championship_id at MAX+1 so position_results lines up even if
        # the table already contains other seasons' rows.
        next_id = (
            conn.execute(
                "SELECT COALESCE(MAX(championship_id), 0) FROM championship_results"
            ).fetchone()[0]
            + 1
        )

        champ_buf: list[tuple] = []
        stand_buf: list[tuple[np.ndarray, np.ndarray]] = []
        inserted = 0

        for i, subset in enumerate(race_combinations(num_races)):
            ordered_drivers, ordered_scores = rank_standings(drivers, scores, subset)
            rounds_str = ",".join(str(r + 1) for r in subset)
            standings_str = ",".join(ordered_drivers.tolist())
            points_str = ",".join(str(int(p)) for p in ordered_scores)
            winner = str(ordered_drivers[0])

            champ_buf.append((season, len(subset), rounds_str, standings_str, winner, points_str))
            stand_buf.append((ordered_drivers, ordered_scores))

            if len(champ_buf) >= batch_size:
                _flush(conn, champ_buf, stand_buf, next_id, season)
                next_id += len(champ_buf)
                inserted += len(champ_buf)
                champ_buf.clear()
                stand_buf.clear()
                if on_progress:
                    on_progress(inserted, total)

        if champ_buf:
            _flush(conn, champ_buf, stand_buf, next_id, season)
            inserted += len(champ_buf)
            if on_progress:
                on_progress(inserted, total)

        conn.commit()
        _restore_safe(conn)
        return inserted
    finally:
        conn.close()


def _flush(
    conn: sqlite3.Connection,
    champ_buf: list[tuple],
    stand_buf: list[tuple[np.ndarray, np.ndarray]],
    start_id: int,
    season: int,
) -> None:
    conn.executemany(INSERT_CHAMPIONSHIP, champ_buf)

    position_rows: list[tuple] = []
    for offset, (ordered_drivers, ordered_scores) in enumerate(stand_buf):
        cid = start_id + offset
        for pos, (driver, points) in enumerate(
            zip(ordered_drivers.tolist(), ordered_scores.tolist()), start=1
        ):
            position_rows.append((cid, driver, pos, int(points), season))
    conn.executemany(INSERT_POSITION, position_rows)


def clear_season(db_path: Path, season: int) -> None:
    """Remove all championship + position rows for a season. Used before reprocess."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("DELETE FROM position_results WHERE season = ?", (season,))
        conn.execute("DELETE FROM championship_results WHERE season = ?", (season,))
        conn.execute("DELETE FROM driver_statistics WHERE season = ?", (season,))
        conn.execute("DELETE FROM win_probability_cache WHERE season = ?", (season,))
        conn.commit()
    finally:
        conn.close()
