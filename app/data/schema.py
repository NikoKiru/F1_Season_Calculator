"""Canonical schema definition — single source of truth.

The database is derived from the season CSVs, so there are no data migrations.
`SCHEMA_VERSION` is kept in `PRAGMA user_version`. When a database carries an
older version, `init_schema` drops what changed shape and every build stamp,
and the next `f1 sync` rebuilds each season into the current layout.
"""
from sqlalchemy import Connection, text

# 2: position tables keyed by (season, entry, position, championship_id) with
#    no rowid and no points column; result tables keep three indexes.
SCHEMA_VERSION = 2

# Run once on a database below SCHEMA_VERSION, before SCHEMA_STATEMENTS. Every
# statement must be safe on an empty file and on any earlier layout.
MIGRATION_STATEMENTS: tuple[str, ...] = (
    "DROP TABLE IF EXISTS position_results",
    "DROP TABLE IF EXISTS constructor_position_results",
    "DROP INDEX IF EXISTS idx_winner",
    "DROP INDEX IF EXISTS idx_num_races",
    "DROP INDEX IF EXISTS idx_winner_num_races",
    "DROP INDEX IF EXISTS idx_season",
    "DROP INDEX IF EXISTS idx_season_winner",
    "DROP INDEX IF EXISTS idx_constructor_winner",
    "DROP INDEX IF EXISTS idx_constructor_num_races",
    "DROP INDEX IF EXISTS idx_constructor_season",
    "DROP INDEX IF EXISTS idx_constructor_season_winner",
    "DROP TABLE IF EXISTS season_builds",
)

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
    # Every index is maintained on each of the 2^N - 1 inserts of a rebuild, so
    # there is one per access path: the scenario search, the season listing
    # (longest first) and one winner's list (longest first).
    "CREATE INDEX IF NOT EXISTS idx_rounds ON championship_results (rounds)",
    "CREATE INDEX IF NOT EXISTS idx_season_num_races ON championship_results (season, num_races)",
    "CREATE INDEX IF NOT EXISTS idx_season_winner_num_races "
    "ON championship_results (season, winner, num_races)",
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
    # One row per entry per scenario, which makes this the bulk of the file.
    # The table is its own index: the key reads "this driver's scenarios at
    # this position, in id order", and ids run shortest scenario first. The
    # points at that position are in championship_results.points.
    """
    CREATE TABLE IF NOT EXISTS position_results (
        season INTEGER NOT NULL,
        driver_code TEXT NOT NULL,
        position INTEGER NOT NULL,
        championship_id INTEGER NOT NULL,
        PRIMARY KEY (season, driver_code, position, championship_id)
    ) WITHOUT ROWID
    """,
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
    # --- Constructors' Championship (WCC) — mirrors the driver tables ---
    """
    CREATE TABLE IF NOT EXISTS constructor_championship_results (
        championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        season INTEGER NOT NULL,
        num_races INTEGER NOT NULL,
        rounds TEXT NOT NULL,
        standings TEXT NOT NULL,
        winner TEXT,
        points TEXT NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_constructor_season_num_races ON constructor_championship_results (season, num_races)",
    "CREATE INDEX IF NOT EXISTS idx_constructor_season_winner_num_races "
    "ON constructor_championship_results (season, winner, num_races)",
    """
    CREATE TABLE IF NOT EXISTS constructor_statistics (
        constructor_name TEXT NOT NULL,
        season INTEGER NOT NULL,
        highest_position INTEGER NOT NULL,
        highest_position_max_races INTEGER,
        highest_position_championship_id INTEGER,
        best_margin INTEGER,
        best_margin_championship_id INTEGER,
        win_count INTEGER DEFAULT 0,
        computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (constructor_name, season)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS constructor_position_results (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        position INTEGER NOT NULL,
        championship_id INTEGER NOT NULL,
        PRIMARY KEY (season, constructor_name, position, championship_id)
    ) WITHOUT ROWID
    """,
    """
    CREATE TABLE IF NOT EXISTS constructor_win_probability_cache (
        constructor_name TEXT NOT NULL,
        num_races INTEGER NOT NULL,
        win_count INTEGER NOT NULL DEFAULT 0,
        total_at_length INTEGER NOT NULL DEFAULT 0,
        season INTEGER NOT NULL,
        PRIMARY KEY (constructor_name, num_races, season)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_constructor_prob_season ON constructor_win_probability_cache (season)",
    """
    CREATE TABLE IF NOT EXISTS constructor_head_to_head (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        opponent TEXT NOT NULL,
        wins INTEGER NOT NULL DEFAULT 0,
        losses INTEGER NOT NULL DEFAULT 0,
        PRIMARY KEY (season, constructor_name, opponent)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_constructor_h2h_season ON constructor_head_to_head (season, constructor_name)",
    """
    CREATE TABLE IF NOT EXISTS constructor_position_distribution (
        season INTEGER NOT NULL,
        constructor_name TEXT NOT NULL,
        position INTEGER NOT NULL,
        count INTEGER NOT NULL,
        PRIMARY KEY (season, constructor_name, position)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS season_builds (
        season INTEGER PRIMARY KEY,
        csv_sha256 TEXT NOT NULL
    )
    """,
)


def init_schema(conn: Connection) -> None:
    """Create what is missing, after bringing an older database forward."""
    version = conn.execute(text("PRAGMA user_version")).scalar_one()
    if version < SCHEMA_VERSION:
        for stmt in MIGRATION_STATEMENTS:
            conn.execute(text(stmt))
    for stmt in SCHEMA_STATEMENTS:
        conn.execute(text(stmt))
    if version < SCHEMA_VERSION:
        conn.execute(text(f"PRAGMA user_version = {SCHEMA_VERSION}"))
    conn.commit()
