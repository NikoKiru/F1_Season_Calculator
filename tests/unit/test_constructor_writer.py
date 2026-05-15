"""Smoke test: constructor writer inserts the expected number of rows."""
from __future__ import annotations

import sqlite3

import numpy as np
from sqlalchemy import create_engine

from app.data.schema import init_schema
from app.pipeline import constructor_writer
from app.pipeline.constructor_builder import LoadedConstructorSeason


def _init_db(path):
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        init_schema(conn)
    engine.dispose()


def test_process_season_inserts_2_pow_n_minus_1_championships(tmp_path):
    db = tmp_path / "wcc.db"
    _init_db(db)

    built = LoadedConstructorSeason(
        constructors=np.array(["TeamA", "TeamB", "TeamC"], dtype=object),
        round_numbers=np.array([1, 2, 3]),
        combined=np.array(
            [
                [30, 10, 20],  # TeamA
                [20, 25, 10],  # TeamB
                [5, 5, 5],     # TeamC
            ]
        ),
    )

    inserted = constructor_writer.process_season(db, built, season=9999, batch_size=2)

    # 2^3 - 1 = 7 subsets, each producing one championship row.
    assert inserted == 7

    conn = sqlite3.connect(db)
    try:
        champ_count = conn.execute(
            "SELECT COUNT(*) FROM constructor_championship_results WHERE season = 9999"
        ).fetchone()[0]
        pos_count = conn.execute(
            "SELECT COUNT(*) FROM constructor_position_results WHERE season = 9999"
        ).fetchone()[0]

        assert champ_count == 7
        # 3 constructors × 7 championships = 21 position rows.
        assert pos_count == 21

        # The full-season winner is TeamA (30+10+20=60 vs TeamB 55, TeamC 15).
        full_season = conn.execute(
            "SELECT winner, standings, points FROM constructor_championship_results "
            "WHERE num_races = 3 AND season = 9999"
        ).fetchone()
        assert full_season[0] == "TeamA"
        assert full_season[1] == "TeamA,TeamB,TeamC"
        assert full_season[2] == "60,55,15"
    finally:
        conn.close()


def test_clear_season_removes_constructor_rows(tmp_path):
    db = tmp_path / "wcc.db"
    _init_db(db)

    built = LoadedConstructorSeason(
        constructors=np.array(["X", "Y"], dtype=object),
        round_numbers=np.array([1, 2]),
        combined=np.array([[10, 10], [5, 5]]),
    )
    constructor_writer.process_season(db, built, season=9999)

    constructor_writer.clear_season(db, 9999)

    conn = sqlite3.connect(db)
    try:
        for table in (
            "constructor_championship_results",
            "constructor_position_results",
            "constructor_statistics",
            "constructor_win_probability_cache",
            "constructor_head_to_head",
            "constructor_position_distribution",
        ):
            c = conn.execute(
                f"SELECT COUNT(*) FROM {table} WHERE season = 9999"
            ).fetchone()[0]
            assert c == 0, f"{table} not cleared"
    finally:
        conn.close()
