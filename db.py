import sqlite3
import click
from flask import current_app, g
from flask.cli import with_appcontext

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
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

@click.command('init-db')
@with_appcontext
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)