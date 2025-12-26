import pytest
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from db import get_db, dispose_all_engines  # noqa: E402


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
        # Initialize the database schema
        db = get_db()
        db.execute("""
        CREATE TABLE IF NOT EXISTS championship_results (
            championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
            num_races INTEGER NOT NULL,
            rounds TEXT NOT NULL,
            standings TEXT NOT NULL,
            winner TEXT,
            points TEXT NOT NULL
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_winner ON championship_results (winner);")
        db.execute("CREATE INDEX IF NOT EXISTS idx_num_races ON championship_results (num_races);")

        # Create driver_statistics table for pre-computed stats
        db.execute("""
        CREATE TABLE IF NOT EXISTS driver_statistics (
            driver_code TEXT PRIMARY KEY,
            highest_position INTEGER NOT NULL,
            highest_position_max_races INTEGER,
            highest_position_championship_id INTEGER,
            best_margin INTEGER,
            best_margin_championship_id INTEGER,
            win_count INTEGER DEFAULT 0,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Create position_results table for fast position queries
        db.execute("""
        CREATE TABLE IF NOT EXISTS position_results (
            championship_id INTEGER NOT NULL,
            driver_code TEXT NOT NULL,
            position INTEGER NOT NULL,
            points INTEGER NOT NULL,
            PRIMARY KEY (championship_id, driver_code),
            FOREIGN KEY (championship_id) REFERENCES championship_results(championship_id)
        );
        """)
        db.execute("CREATE INDEX IF NOT EXISTS idx_driver_position ON position_results (driver_code, position);")

        # Insert sample test data
        sample_data = [
            (3, '1,2,3', 'VER,NOR,LEC,HAM,RUS', 'VER', '68,61,48,45,42'),
            (5, '1,2,3,4,5', 'NOR,VER,LEC,HAM,PIA', 'NOR', '113,108,95,88,82'),
            (4, '1,2,3,4', 'VER,LEC,NOR,HAM,RUS', 'VER', '90,78,75,70,65'),
            (6, '1,2,3,4,5,6', 'VER,NOR,LEC,PIA,HAM', 'VER', '138,130,118,105,98'),
            (3, '1,2,3', 'LEC,VER,NOR,HAM,RUS', 'LEC', '70,65,58,50,45'),
        ]
        db.executemany("""
            INSERT INTO championship_results (num_races, rounds, standings, winner, points)
            VALUES (?, ?, ?, ?, ?)
        """, sample_data)

        # Insert position_results for each championship
        # Championship 1: VER,NOR,LEC,HAM,RUS with points 68,61,48,45,42
        # Championship 2: NOR,VER,LEC,HAM,PIA with points 113,108,95,88,82
        # Championship 3: VER,LEC,NOR,HAM,RUS with points 90,78,75,70,65
        # Championship 4: VER,NOR,LEC,PIA,HAM with points 138,130,118,105,98
        # Championship 5: LEC,VER,NOR,HAM,RUS with points 70,65,58,50,45
        position_data = [
            # Championship 1
            (1, 'VER', 1, 68), (1, 'NOR', 2, 61), (1, 'LEC', 3, 48), (1, 'HAM', 4, 45), (1, 'RUS', 5, 42),
            # Championship 2
            (2, 'NOR', 1, 113), (2, 'VER', 2, 108), (2, 'LEC', 3, 95), (2, 'HAM', 4, 88), (2, 'PIA', 5, 82),
            # Championship 3
            (3, 'VER', 1, 90), (3, 'LEC', 2, 78), (3, 'NOR', 3, 75), (3, 'HAM', 4, 70), (3, 'RUS', 5, 65),
            # Championship 4
            (4, 'VER', 1, 138), (4, 'NOR', 2, 130), (4, 'LEC', 3, 118), (4, 'PIA', 4, 105), (4, 'HAM', 5, 98),
            # Championship 5
            (5, 'LEC', 1, 70), (5, 'VER', 2, 65), (5, 'NOR', 3, 58), (5, 'HAM', 4, 50), (5, 'RUS', 5, 45),
        ]
        db.executemany("""
            INSERT INTO position_results (championship_id, driver_code, position, points)
            VALUES (?, ?, ?, ?)
        """, position_data)

        # Insert pre-computed driver statistics for tests
        # VER: P1, 6 races, margin 8 (138-130), 3 wins
        # NOR: P1, 5 races, margin 5 (113-108), 1 win
        # LEC: P1, 3 races, margin 5 (70-65), 1 win
        # HAM: P4, 6 races, no margin (never won)
        # RUS: P5, 4 races, no margin
        # PIA: P4, 6 races, no margin
        stats_data = [
            ('VER', 1, 6, 4, 8, 4, 3),    # P1, best at 6 races, margin +8, 3 wins
            ('NOR', 1, 5, 2, 5, 2, 1),    # P1, best at 5 races, margin +5, 1 win
            ('LEC', 1, 3, 5, 5, 5, 1),    # P1, best at 3 races, margin +5, 1 win
            ('HAM', 4, 6, 4, None, None, 0),
            ('RUS', 5, 4, 3, None, None, 0),
            ('PIA', 4, 6, 4, None, None, 0),
        ]
        db.executemany("""
            INSERT INTO driver_statistics
            (driver_code, highest_position, highest_position_max_races,
             highest_position_championship_id, best_margin, best_margin_championship_id, win_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, stats_data)

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
