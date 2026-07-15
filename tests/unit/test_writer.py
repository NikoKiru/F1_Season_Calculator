"""Writer id-alignment tests.

`championship_results` uses AUTOINCREMENT, so after a clear_season +
process_season cycle (the `sync` / `add-race` rebuild path) SQLite's
sqlite_sequence keeps counting from the old maximum. The writer must not
predict ids from MAX(championship_id) alone or every position_results row
ends up pointing at championship ids that no longer exist.
"""
from __future__ import annotations

import sqlite3

import numpy as np
from sqlalchemy import create_engine

from app.data.schema import init_schema
from app.pipeline import constructor_writer, writer
from app.pipeline.constructor_builder import LoadedConstructorSeason
from app.pipeline.csv_loader import LoadedSeason


def _init_db(path):
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        init_schema(conn)
    engine.dispose()


def _loaded_season() -> LoadedSeason:
    race = np.array([[25, 18, 25], [18, 25, 18], [15, 15, 15]])
    return LoadedSeason(
        drivers=np.array(["VER", "NOR", "LEC"], dtype=object),
        round_numbers=np.array([1, 2, 3]),
        race_scores=race,
        sprint_scores=np.zeros_like(race),
    )


def _built_constructor_season() -> LoadedConstructorSeason:
    return LoadedConstructorSeason(
        constructors=np.array(["TeamA", "TeamB"], dtype=object),
        round_numbers=np.array([1, 2, 3]),
        combined=np.array([[30, 10, 20], [20, 25, 10]]),
    )


def _assert_positions_join(conn: sqlite3.Connection, champ_table: str, pos_table: str,
                           entity_col: str, season: int) -> None:
    total = conn.execute(
        f"SELECT COUNT(*) FROM {pos_table} WHERE season = ?", (season,)
    ).fetchone()[0]
    joined = conn.execute(
        f"SELECT COUNT(*) FROM {pos_table} pr "
        f"JOIN {champ_table} cr ON pr.championship_id = cr.championship_id "
        f"WHERE pr.season = ?",
        (season,),
    ).fetchone()[0]
    assert total > 0
    assert joined == total, (
        f"{joined} of {total} {pos_table} rows join to {champ_table} — id drift"
    )
    # The position-1 entity must be the stored winner for every championship.
    mismatches = conn.execute(
        f"SELECT COUNT(*) FROM {pos_table} pr "
        f"JOIN {champ_table} cr ON pr.championship_id = cr.championship_id "
        f"WHERE pr.season = ? AND pr.position = 1 AND pr.{entity_col} != cr.winner",
        (season,),
    ).fetchone()[0]
    assert mismatches == 0


def test_rebuild_after_clear_keeps_position_ids_aligned(tmp_path):
    db = tmp_path / "wdc.db"
    _init_db(db)
    loaded = _loaded_season()

    writer.process_season(db, loaded, season=9999)
    # The sync path: clear + reprocess into the same file. AUTOINCREMENT keeps
    # counting from sqlite_sequence, so predicted ids drift unless explicit.
    writer.clear_season(db, 9999)
    writer.process_season(db, loaded, season=9999)

    conn = sqlite3.connect(db)
    try:
        _assert_positions_join(
            conn, "championship_results", "position_results", "driver_code", 9999
        )
    finally:
        conn.close()


def test_constructor_rebuild_after_clear_keeps_position_ids_aligned(tmp_path):
    db = tmp_path / "wcc.db"
    _init_db(db)
    built = _built_constructor_season()

    constructor_writer.process_season(db, built, season=9999)
    constructor_writer.clear_season(db, 9999)
    constructor_writer.process_season(db, built, season=9999)

    conn = sqlite3.connect(db)
    try:
        _assert_positions_join(
            conn,
            "constructor_championship_results",
            "constructor_position_results",
            "constructor_name",
            9999,
        )
    finally:
        conn.close()


def test_multi_season_rebuild_does_not_collide_with_other_seasons(tmp_path):
    """Rebuilding one season must leave other seasons' rows untouched and
    keep the rebuilt season's ids unique against them."""
    db = tmp_path / "multi.db"
    _init_db(db)
    loaded = _loaded_season()

    writer.process_season(db, loaded, season=2025)
    writer.process_season(db, loaded, season=2026)
    writer.clear_season(db, 2026)
    writer.process_season(db, loaded, season=2026)

    conn = sqlite3.connect(db)
    try:
        dup = conn.execute(
            "SELECT COUNT(*) FROM (SELECT championship_id FROM championship_results "
            "GROUP BY championship_id HAVING COUNT(*) > 1)"
        ).fetchone()[0]
        assert dup == 0
        _assert_positions_join(
            conn, "championship_results", "position_results", "driver_code", 2025
        )
        _assert_positions_join(
            conn, "championship_results", "position_results", "driver_code", 2026
        )
    finally:
        conn.close()
