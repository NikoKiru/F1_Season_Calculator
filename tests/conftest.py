import pytest
import os
import sys
import tempfile

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app as flask_app  # noqa: E402
from db import get_db  # noqa: E402


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

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
