"""Highest-position exactness tests for stats_compute.

The highest-position scan must consider every championship. A sampled scan
(e.g. `ORDER BY championship_id DESC LIMIT 10000` per length) silently reports
wrong `highest_position_max_races` once a season length has more than 10,000
combinations (16+ rounds), because a driver's best long-season result can live
entirely in the lexicographically-first combinations that the sample skips.

Scenario (16 rounds, 3 entrants):
    AAA scores 50 every round               -> always P1.
    BBB scores 10 every round.
    CCC scores 11 in rounds 1-9, 1 after    -> beats BBB exactly on the
        non-empty subsets of rounds {1..9}.

CCC's best result is P2, and the longest championship where it happens is the
9-round combination {1..9} — the lexicographically FIRST combination at length
9 (C(16,9) = 11,440 > 10,000), which a DESC-limited sample never sees.
"""
from __future__ import annotations

import sqlite3

import numpy as np
from sqlalchemy import create_engine

from app.data.schema import init_schema
from app.pipeline import constructor_stats_compute, constructor_writer, stats_compute, writer
from app.pipeline.constructor_builder import LoadedConstructorSeason
from app.pipeline.csv_loader import LoadedSeason

N_ROUNDS = 16
SEASON = 9998


def _scores() -> np.ndarray:
    a = [50] * N_ROUNDS
    b = [10] * N_ROUNDS
    c = [11] * 9 + [1] * (N_ROUNDS - 9)
    return np.array([a, b, c])


def _init_db(path):
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        init_schema(conn)
    engine.dispose()


def test_driver_highest_position_is_exact_beyond_sample_window(tmp_path):
    db = tmp_path / "wdc.db"
    _init_db(db)
    scores = _scores()
    loaded = LoadedSeason(
        drivers=np.array(["AAA", "BBB", "CCC"], dtype=object),
        round_numbers=np.arange(1, N_ROUNDS + 1),
        race_scores=scores,
        sprint_scores=np.zeros_like(scores),
    )
    writer.process_season(db, loaded, season=SEASON)
    stats_compute.compute(db, SEASON)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT highest_position, highest_position_max_races "
            "FROM driver_statistics WHERE season = ? AND driver_code = 'CCC'",
            (SEASON,),
        ).fetchone()
        assert row["highest_position"] == 2
        # Longest P2 championship for CCC is the 9-round combo {1..9}.
        assert row["highest_position_max_races"] == 9

        # General invariant: highest_position matches the exact per-position
        # distribution derived from every championship.
        mismatches = conn.execute(
            "SELECT COUNT(*) FROM driver_statistics ds "
            "JOIN (SELECT driver_code, MIN(position) AS best "
            "      FROM driver_position_distribution WHERE season = ? "
            "      GROUP BY driver_code) d ON d.driver_code = ds.driver_code "
            "WHERE ds.season = ? AND ds.highest_position != d.best",
            (SEASON, SEASON),
        ).fetchone()[0]
        assert mismatches == 0
    finally:
        conn.close()


def test_constructor_highest_position_is_exact_beyond_sample_window(tmp_path):
    db = tmp_path / "wcc.db"
    _init_db(db)
    built = LoadedConstructorSeason(
        constructors=np.array(["TeamA", "TeamB", "TeamC"], dtype=object),
        round_numbers=np.arange(1, N_ROUNDS + 1),
        combined=_scores(),
    )
    constructor_writer.process_season(db, built, season=SEASON)
    constructor_stats_compute.compute(db, SEASON)

    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute(
            "SELECT highest_position, highest_position_max_races "
            "FROM constructor_statistics "
            "WHERE season = ? AND constructor_name = 'TeamC'",
            (SEASON,),
        ).fetchone()
        assert row["highest_position"] == 2
        assert row["highest_position_max_races"] == 9
    finally:
        conn.close()
