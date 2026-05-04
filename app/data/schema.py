"""Canonical schema definition — single source of truth.

Schema matches the old db.py exactly so both apps can read the same SQLite
file during parallel-run. When we introduce Alembic migrations, the baseline
revision captures this schema.
"""
from sqlalchemy import Connection, text


SCHEMA_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS championship_results (
        championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER NOT NULL DEFAULT 2025,
        num_races INTEGER NOT NULL,
        rounds TEXT NOT NULL,
        standings TEXT NOT NULL,
        winner TEXT,
        points TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_winner ON championship_results (winner)",
    "CREATE INDEX IF NOT EXISTS idx_num_races ON championship_results (num_races)",
    "CREATE INDEX IF NOT EXISTS idx_winner_num_races ON championship_results (winner, num_races)",
    "CREATE INDEX IF NOT EXISTS idx_rounds ON championship_results (rounds)",
    "CREATE INDEX IF NOT EXISTS idx_season ON championship_results (season)",
    "CREATE INDEX IF NOT EXISTS idx_season_winner ON championship_results (season, winner)",
    """
    CREATE TABLE IF NOT EXISTS driver_statistics (
        driver_code TEXT NOT NULL,
        season INTEGER NOT NULL DEFAULT 2025,
        highest_position INTEGER NOT NULL,
        highest_position_max_races INTEGER,
        highest_position_championship_id INTEGER,
        best_margin INTEGER,
        best_margin_championship_id INTEGER,
        win_count INTEGER DEFAULT 0,
        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (driver_code, season)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS position_results (
        championship_id INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        position INTEGER NOT NULL,
        points INTEGER NOT NULL,
        season INTEGER NOT NULL DEFAULT 2025,
        PRIMARY KEY (championship_id, driver_code),
        FOREIGN KEY (championship_id) REFERENCES championship_results(championship_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_driver_position ON position_results (driver_code, position)",
    "CREATE INDEX IF NOT EXISTS idx_position_season ON position_results (season, driver_code, position)",
    """
    CREATE TABLE IF NOT EXISTS win_probability_cache (
        driver_code TEXT NOT NULL,
        num_races INTEGER NOT NULL,
        win_count INTEGER NOT NULL DEFAULT 0,
        total_at_length INTEGER NOT NULL DEFAULT 0,
        season INTEGER NOT NULL DEFAULT 2025,
        PRIMARY KEY (driver_code, num_races, season)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_prob_driver ON win_probability_cache (driver_code)",
    "CREATE INDEX IF NOT EXISTS idx_prob_num_races ON win_probability_cache (num_races)",
    "CREATE INDEX IF NOT EXISTS idx_prob_season ON win_probability_cache (season)",
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
)


def init_schema(conn: Connection) -> None:
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(text(stmt))
    conn.commit()
