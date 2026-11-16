"""Schema versioning: a database from an older layout is brought forward.

The database is derived from the season CSVs, so bringing it forward means
dropping what changed shape and letting the next sync rebuild it.
"""
from __future__ import annotations

import sqlite3

import pytest
from sqlalchemy import create_engine

from app.data import schema
from app.data.schema import init_schema

# The position tables and indexes as they were before schema version 2.
OLD_LAYOUT = (
    """
    CREATE TABLE championship_results (
        championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER NOT NULL DEFAULT 2025,
        num_races INTEGER NOT NULL,
        rounds TEXT NOT NULL,
        standings TEXT NOT NULL,
        winner TEXT,
        points TEXT NOT NULL
    )
    """,
    "CREATE INDEX idx_winner ON championship_results (winner)",
    "CREATE INDEX idx_season ON championship_results (season)",
    """
    CREATE TABLE position_results (
        championship_id INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        position INTEGER NOT NULL,
        points INTEGER NOT NULL,
        season INTEGER NOT NULL DEFAULT 2025,
        PRIMARY KEY (championship_id, driver_code)
    )
    """,
    "CREATE INDEX idx_driver_position ON position_results (driver_code, position)",
    """
    CREATE TABLE constructor_position_results (
        championship_id INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        position INTEGER NOT NULL,
        points INTEGER NOT NULL,
        season INTEGER NOT NULL,
        PRIMARY KEY (championship_id, constructor_name)
    )
    """,
    "CREATE TABLE season_builds (season INTEGER PRIMARY KEY, csv_sha256 TEXT NOT NULL)",
    "INSERT INTO championship_results VALUES (1, 2026, 1, '1', 'VER,NOR', 'VER', '25,18')",
    "INSERT INTO position_results VALUES (1, 'VER', 1, 25, 2026)",
    "INSERT INTO season_builds VALUES (2026, 'abc')",
)


def _migrate(path) -> None:
    engine = create_engine(f"sqlite:///{path}", future=True)
    with engine.begin() as conn:
        init_schema(conn)
    engine.dispose()


@pytest.fixture
def old_db(tmp_path):
    path = tmp_path / "old.db"
    con = sqlite3.connect(path)
    for statement in OLD_LAYOUT:
        con.execute(statement)
    con.commit()
    con.close()
    return path


def _columns(con: sqlite3.Connection, table: str) -> list[str]:
    return [row[1] for row in con.execute(f"PRAGMA table_info({table})")]


def _indexes(con: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in con.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
    }


def test_new_database_is_stamped_with_the_schema_version(tmp_path):
    path = tmp_path / "new.db"
    _migrate(path)
    con = sqlite3.connect(path)
    try:
        assert con.execute("PRAGMA user_version").fetchone()[0] == schema.SCHEMA_VERSION
    finally:
        con.close()


def test_old_position_tables_are_replaced_by_the_keyed_layout(old_db):
    _migrate(old_db)
    con = sqlite3.connect(old_db)
    try:
        assert _columns(con, "position_results") == [
            "season", "driver_code", "position", "championship_id",
        ]
        assert _columns(con, "constructor_position_results") == [
            "season", "constructor_name", "position", "championship_id",
        ]
        assert con.execute("SELECT COUNT(*) FROM position_results").fetchone()[0] == 0
    finally:
        con.close()


def test_migration_drops_the_indexes_nothing_reads_anymore(old_db):
    _migrate(old_db)
    con = sqlite3.connect(old_db)
    try:
        indexes = _indexes(con)
        assert "idx_winner" not in indexes
        assert "idx_season" not in indexes
        assert "idx_driver_position" not in indexes
        assert "idx_season_winner_num_races" in indexes
    finally:
        con.close()


def test_migration_keeps_the_championships_but_marks_every_season_stale(old_db):
    # Position rows are gone, so each season has to be rebuilt before it is
    # trusted again: the build stamps go, the next sync does the rest.
    _migrate(old_db)
    con = sqlite3.connect(old_db)
    try:
        assert con.execute("SELECT COUNT(*) FROM championship_results").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM season_builds").fetchone()[0] == 0
    finally:
        con.close()


def test_a_current_database_is_left_alone(tmp_path):
    path = tmp_path / "current.db"
    _migrate(path)
    con = sqlite3.connect(path)
    con.execute("INSERT INTO season_builds VALUES (2026, 'abc')")
    con.execute("INSERT INTO position_results VALUES (2026, 'VER', 1, 1)")
    con.commit()
    con.close()

    _migrate(path)

    con = sqlite3.connect(path)
    try:
        assert con.execute("SELECT COUNT(*) FROM season_builds").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM position_results").fetchone()[0] == 1
    finally:
        con.close()
