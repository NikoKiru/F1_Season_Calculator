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
        db.commit()

    yield flask_app

    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
