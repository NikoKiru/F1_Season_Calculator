import pytest
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from db import get_db, dispose_all_engines  # noqa: E402
from championship.models import DEFAULT_SEASON  # noqa: E402


# Test data uses the app's default season so queries without ?season= find data
TEST_SEASON = DEFAULT_SEASON


@pytest.fixture
def app():
    """Create application for testing with a temporary database."""

    # Create a temporary database file
    db_fd, db_path = tempfile.mkstemp()

    flask_app.config.update({
        "TESTING": True,
        "DATABASE": db_path,
    })

    with flask_app.app_context():
        # Initialize the database schema (matches db.py init_db)
        db = get_db()
        db.execute("""
        CREATE TABLE IF NOT EXISTS championship_results (
            championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            season INTEGER NOT NULL DEFAULT 2025,
            num_races INTEGER NOT NULL,
            rounds TEXT NOT NULL,
            standings TEXT NOT NULL,
            winner TEXT,
            points TEXT NOT NULL
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_winner ON championship_results (winner);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_num_races ON championship_results (num_races);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_season ON championship_results (season);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_season_winner ON championship_results (season, winner);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_winner_num_races ON championship_results (winner, num_races);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_rounds ON championship_results (rounds);")

        # Create driver_statistics table with season support
        db.execute("""
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
        );
        """)

        # Create position_results table with season support
        db.execute("""
        CREATE TABLE IF NOT EXISTS position_results (
            championship_id INTEGER NOT NULL,
            driver_code TEXT NOT NULL,
            position INTEGER NOT NULL,
            points INTEGER NOT NULL,
            season INTEGER NOT NULL DEFAULT 2025,
            PRIMARY KEY (championship_id, driver_code),
            FOREIGN KEY (championship_id) REFERENCES championship_results(championship_id)
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_driver_position ON position_results (driver_code, position);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_position_season ON position_results (season, driver_code, position);")

        # Create win_probability_cache table with season support
        db.execute("""
        CREATE TABLE IF NOT EXISTS win_probability_cache (
            driver_code TEXT NOT NULL,
            num_races INTEGER NOT NULL,
            win_count INTEGER NOT NULL DEFAULT 0,
            total_at_length INTEGER NOT NULL DEFAULT 0,
            season INTEGER NOT NULL DEFAULT 2025,
            PRIMARY KEY (driver_code, num_races, season)
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_prob_driver ON win_probability_cache (driver_code);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_prob_num_races ON win_probability_cache (num_races);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_prob_season ON win_probability_cache (season);")

        # Insert sample test data for season 2025
        sample_data = [
            (TEST_SEASON, 3, '1,2,3', 'VER,NOR,LEC,HAM,RUS', 'VER', '68,61,48,45,42'),
            (TEST_SEASON, 5, '1,2,3,4,5', 'NOR,VER,LEC,HAM,PIA', 'NOR', '113,108,95,88,82'),
            (TEST_SEASON, 4, '1,2,3,4', 'VER,LEC,NOR,HAM,RUS', 'VER', '90,78,75,70,65'),
            (TEST_SEASON, 6, '1,2,3,4,5,6', 'VER,NOR,LEC,PIA,HAM', 'VER', '138,130,118,105,98'),
            (TEST_SEASON, 3, '1,2,3', 'LEC,VER,NOR,HAM,RUS', 'LEC', '70,65,58,50,45'),
        ]
        db.executemany("""
            INSERT INTO championship_results (season, num_races, rounds, standings, winner, points)
            VALUES (?, ?, ?, ?, ?, ?)
        """, sample_data)

        # Insert position_results for each championship (with season)
        position_data = [
            # Championship 1: VER,NOR,LEC,HAM,RUS
            (1, 'VER', 1, 68, TEST_SEASON), (1, 'NOR', 2, 61, TEST_SEASON),
            (1, 'LEC', 3, 48, TEST_SEASON), (1, 'HAM', 4, 45, TEST_SEASON),
            (1, 'RUS', 5, 42, TEST_SEASON),
            # Championship 2: NOR,VER,LEC,HAM,PIA
            (2, 'NOR', 1, 113, TEST_SEASON), (2, 'VER', 2, 108, TEST_SEASON),
            (2, 'LEC', 3, 95, TEST_SEASON), (2, 'HAM', 4, 88, TEST_SEASON),
            (2, 'PIA', 5, 82, TEST_SEASON),
            # Championship 3: VER,LEC,NOR,HAM,RUS
            (3, 'VER', 1, 90, TEST_SEASON), (3, 'LEC', 2, 78, TEST_SEASON),
            (3, 'NOR', 3, 75, TEST_SEASON), (3, 'HAM', 4, 70, TEST_SEASON),
            (3, 'RUS', 5, 65, TEST_SEASON),
            # Championship 4: VER,NOR,LEC,PIA,HAM
            (4, 'VER', 1, 138, TEST_SEASON), (4, 'NOR', 2, 130, TEST_SEASON),
            (4, 'LEC', 3, 118, TEST_SEASON), (4, 'PIA', 4, 105, TEST_SEASON),
            (4, 'HAM', 5, 98, TEST_SEASON),
            # Championship 5: LEC,VER,NOR,HAM,RUS
            (5, 'LEC', 1, 70, TEST_SEASON), (5, 'VER', 2, 65, TEST_SEASON),
            (5, 'NOR', 3, 58, TEST_SEASON), (5, 'HAM', 4, 50, TEST_SEASON),
            (5, 'RUS', 5, 45, TEST_SEASON),
        ]
        db.executemany("""
            INSERT INTO position_results (championship_id, driver_code, position, points, season)
            VALUES (?, ?, ?, ?, ?)
        """, position_data)

        # Insert pre-computed driver statistics with season
        stats_data = [
            ('VER', TEST_SEASON, 1, 6, 4, 8, 4, 3),
            ('NOR', TEST_SEASON, 1, 5, 2, 5, 2, 1),
            ('LEC', TEST_SEASON, 1, 3, 5, 5, 5, 1),
            ('HAM', TEST_SEASON, 4, 6, 4, None, None, 0),
            ('RUS', TEST_SEASON, 5, 4, 3, None, None, 0),
            ('PIA', TEST_SEASON, 4, 6, 4, None, None, 0),
        ]
        db.executemany("""
            INSERT INTO driver_statistics
            (driver_code, season, highest_position, highest_position_max_races,
             highest_position_championship_id, best_margin, best_margin_championship_id, win_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, stats_data)

        # Insert pre-computed win probability cache data with season
        prob_cache_data = [
            # VER
            ('VER', 3, 1, 2, TEST_SEASON), ('VER', 4, 1, 1, TEST_SEASON),
            ('VER', 5, 0, 1, TEST_SEASON), ('VER', 6, 1, 1, TEST_SEASON),
            # NOR
            ('NOR', 3, 0, 2, TEST_SEASON), ('NOR', 4, 0, 1, TEST_SEASON),
            ('NOR', 5, 1, 1, TEST_SEASON), ('NOR', 6, 0, 1, TEST_SEASON),
            # LEC
            ('LEC', 3, 1, 2, TEST_SEASON), ('LEC', 4, 0, 1, TEST_SEASON),
            ('LEC', 5, 0, 1, TEST_SEASON), ('LEC', 6, 0, 1, TEST_SEASON),
            # HAM
            ('HAM', 3, 0, 2, TEST_SEASON), ('HAM', 4, 0, 1, TEST_SEASON),
            ('HAM', 5, 0, 1, TEST_SEASON), ('HAM', 6, 0, 1, TEST_SEASON),
            # RUS
            ('RUS', 3, 0, 2, TEST_SEASON), ('RUS', 4, 0, 1, TEST_SEASON),
            ('RUS', 5, 0, 1, TEST_SEASON), ('RUS', 6, 0, 1, TEST_SEASON),
            # PIA
            ('PIA', 3, 0, 2, TEST_SEASON), ('PIA', 4, 0, 1, TEST_SEASON),
            ('PIA', 5, 0, 1, TEST_SEASON), ('PIA', 6, 0, 1, TEST_SEASON),
        ]
        db.executemany("""
            INSERT INTO win_probability_cache (driver_code, num_races, win_count, total_at_length, season)
            VALUES (?, ?, ?, ?, ?)
        """, prob_cache_data)

        db.commit()

    yield flask_app

    # Cleanup: dispose engines before deleting database file
    dispose_all_engines()
    os.close(db_fd)
    try:
        os.unlink(db_path)
        # Also clean up WAL and SHM files if they exist
        wal_path = db_path + "-wal"
        shm_path = db_path + "-shm"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
        if os.path.exists(shm_path):
            os.unlink(shm_path)
    except PermissionError:
        pass  # File may still be locked on Windows


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
