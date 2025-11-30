import sqlite3
from typing import Optional
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db() -> sqlite3.Connection:
    """Return a SQLite connection for the current Flask application context.

    The connection is stored in `flask.g` for reuse within the request.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e: Optional[Exception] = None) -> None:
    """Close the database connection if present in the Flask `g` object."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    # Performance-related PRAGMAs: safe defaults for general use
    # WAL improves concurrency; normal synchronous keeps durability while faster than FULL
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    db.execute("PRAGMA temp_store=MEMORY;")
    db.execute("PRAGMA cache_size=-50000;")  # roughly ~50MB cache
    # Create table with a dedicated 'winner' column
    db.execute("""
    CREATE TABLE IF NOT EXISTS championship_results (
        championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_races INTEGER,
        rounds TEXT,
        standings TEXT,
        winner TEXT,
        points TEXT
    );
    """)
    # Create indexes to speed up queries
    db.execute("CREATE INDEX IF NOT EXISTS idx_winner ON championship_results (winner);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_num_races ON championship_results (num_races);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_winner_num_races ON championship_results (winner, num_races);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_points ON championship_results (points);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rounds ON championship_results (rounds);")

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)