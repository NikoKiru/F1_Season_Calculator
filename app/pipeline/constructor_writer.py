"""Batch-insert generated constructor championships into SQLite.

Mirror of `app/pipeline/writer.py` that targets the `constructor_*` tables.
Identical batch + PRAGMA structure so the perf profile carries over.
"""
from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path

import numpy as np

from app.pipeline.combinator import race_combinations, rank_standings, total_combinations
from app.pipeline.constructor_builder import LoadedConstructorSeason

INSERT_CHAMPIONSHIP = (
    "INSERT INTO constructor_championship_results "
    "(season, num_races, rounds, standings, winner, points) "
    "VALUES (?, ?, ?, ?, ?, ?)"
)
INSERT_POSITION = (
    "INSERT INTO constructor_position_results "
    "(championship_id, constructor_name, position, points, season) "
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
    built: LoadedConstructorSeason,
    season: int,
    batch_size: int = 100_000,
    on_progress: Callable[[int, int], None] | None = None,
) -> int:
    constructors = built.constructors
    scores = built.combined
    round_numbers = built.round_numbers.tolist()
    num_weekends = scores.shape[1]
    total = total_combinations(num_weekends)

    conn = sqlite3.connect(db_path)
    try:
        _tune_for_bulk_load(conn)
        conn.execute("BEGIN IMMEDIATE")

        next_id = (
            conn.execute(
                "SELECT COALESCE(MAX(championship_id), 0) "
                "FROM constructor_championship_results"
            ).fetchone()[0]
            + 1
        )

        champ_buf: list[tuple] = []
        stand_buf: list[tuple[np.ndarray, np.ndarray]] = []
        inserted = 0

        for subset in race_combinations(num_weekends):
            ordered, ordered_scores = rank_standings(constructors, scores, subset)
            rounds_str = ",".join(str(round_numbers[i]) for i in subset)
            standings_str = ",".join(ordered.tolist())
            points_str = ",".join(str(int(p)) for p in ordered_scores)
            winner = str(ordered[0])

            champ_buf.append(
                (season, len(subset), rounds_str, standings_str, winner, points_str)
            )
            stand_buf.append((ordered, ordered_scores))

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
    for offset, (ordered, ordered_scores) in enumerate(stand_buf):
        cid = start_id + offset
        for pos, (label, points) in enumerate(
            zip(ordered.tolist(), ordered_scores.tolist(), strict=True), start=1
        ):
            position_rows.append((cid, label, pos, int(points), season))
    conn.executemany(INSERT_POSITION, position_rows)


def clear_season(db_path: Path, season: int) -> None:
    """Remove every constructor cache for a season — used before a reprocess."""
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "DELETE FROM constructor_position_results WHERE season = ?", (season,)
        )
        conn.execute(
            "DELETE FROM constructor_championship_results WHERE season = ?", (season,)
        )
        conn.execute(
            "DELETE FROM constructor_statistics WHERE season = ?", (season,)
        )
        conn.execute(
            "DELETE FROM constructor_win_probability_cache WHERE season = ?", (season,)
        )
        conn.execute(
            "DELETE FROM constructor_head_to_head WHERE season = ?", (season,)
        )
        conn.execute(
            "DELETE FROM constructor_position_distribution WHERE season = ?", (season,)
        )
        conn.commit()
    finally:
        conn.close()
