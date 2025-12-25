import sqlite3
import os
from typing import Optional, TYPE_CHECKING
import click
from flask import current_app, g
from flask.cli import with_appcontext

if TYPE_CHECKING:
    from flask import Flask


def get_db() -> sqlite3.Connection:
    """Return a SQLite connection for the current Flask application context.

    The connection is stored in `flask.g` for reuse within the request.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE']

        # Ensure the directory for the database exists
        db_dir = os.path.dirname(db_path)
        if db_dir and not os.path.exists(db_dir):
            try:
                os.makedirs(db_dir, exist_ok=True)
                click.echo(f"Created directory: {db_dir}")
            except OSError as e:
                click.echo(f"Error creating directory {db_dir}: {e}", err=True)
                raise

        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e: Optional[Exception] = None) -> None:
    """Close the database connection if present in the Flask `g` object."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db(clear_existing: bool = False) -> None:
    """Initialize the database with optimized settings and schema.

    Args:
        clear_existing: If True, drops existing tables before recreating them.
    """
    db_path = current_app.config['DATABASE']

    # Check if database already exists
    db_exists = os.path.exists(db_path)

    if clear_existing and db_exists:
        click.echo(f"Clearing existing database at: {db_path}")
        try:
            os.remove(db_path)
            db_exists = False
        except OSError as e:
            click.echo(f"Warning: Could not remove existing database: {e}", err=True)

    db = get_db()

    click.echo(f"Database location: {db_path}")
    click.echo(f"Database {'already exists' if db_exists else 'will be created'}")

    # Performance-related PRAGMAs: safe defaults for general use
    # WAL improves concurrency; normal synchronous keeps durability while faster than FULL
    click.echo("Applying database performance optimizations...")
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("PRAGMA synchronous=NORMAL;")
    db.execute("PRAGMA temp_store=MEMORY;")
    db.execute("PRAGMA cache_size=-50000;")  # roughly ~50MB cache
    db.execute("PRAGMA mmap_size=268435456;")  # 256MB memory-mapped I/O

    # Create table with a dedicated 'winner' column
    click.echo("Creating championship_results table...")
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

    # Create indexes to speed up queries
    click.echo("Creating indexes for optimized queries...")
    db.execute("CREATE INDEX IF NOT EXISTS idx_winner ON championship_results (winner);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_num_races ON championship_results (num_races);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_winner_num_races ON championship_results (winner, num_races);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_points ON championship_results (points);")
    db.execute("CREATE INDEX IF NOT EXISTS idx_rounds ON championship_results (rounds);")

    # Create pre-computed driver statistics table for instant queries
    click.echo("Creating driver_statistics table...")
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

    db.commit()

    # Get table info
    cursor = db.execute("SELECT COUNT(*) as count FROM championship_results;")
    row_count = cursor.fetchone()[0]
    click.echo(f"Database initialized successfully. Current row count: {row_count}")


@click.command('init-db')
@click.option('--clear', is_flag=True, help='Clear existing database before initializing')
@with_appcontext
def init_db_command(clear: bool) -> None:
    """Initialize the database schema and apply performance optimizations.

    Creates the instance directory if needed, sets up the championship_results
    table with indexes, and applies SQLite performance PRAGMAs.
    """
    init_db(clear_existing=clear)
    click.echo('[OK] Database initialization complete.')


@click.command('setup')
@with_appcontext
def setup_command() -> None:
    """Set up the application for first-time use.

    Creates necessary directories (data/, instance/) and provides guidance
    on next steps.
    """
    click.echo("Setting up F1 Season Calculator...")

    # Create data folder
    data_folder = current_app.config['DATA_FOLDER']
    if not os.path.exists(data_folder):
        try:
            os.makedirs(data_folder, exist_ok=True)
            click.echo(f"[OK] Created data folder: {data_folder}")
        except OSError as e:
            click.echo(f"[ERROR] Error creating data folder: {e}", err=True)
            return
    else:
        click.echo(f"[OK] Data folder already exists: {data_folder}")

    # Check for CSV file
    csv_path = os.path.join(data_folder, "championships.csv")
    if not os.path.exists(csv_path):
        click.echo(f"\n[WARNING] CSV file not found: {csv_path}")
        click.echo("\nPlease create a championships.csv file with the following format:")
        click.echo("  Driver,1,2,3,4,...")
        click.echo("  VER,25,18,25,15,...")
        click.echo("  NOR,18,25,18,25,...")
        click.echo("  LEC,15,15,15,18,...")
        click.echo("\nWhere:")
        click.echo("  - First column: Driver abbreviation (e.g., VER, NOR, LEC)")
        click.echo("  - Subsequent columns: Points for each race (numbered 1, 2, 3, ...)")

        # Create a sample CSV
        sample_csv = os.path.join(data_folder, "championships_sample.csv")
        try:
            with open(sample_csv, 'w') as f:
                f.write("Driver,1,2,3\n")
                f.write("VER,25,18,25\n")
                f.write("NOR,18,25,18\n")
                f.write("LEC,15,15,15\n")
            click.echo(f"\n[OK] Created sample file: {sample_csv}")
            click.echo("  You can rename this to championships.csv or create your own.")
        except OSError as e:
            click.echo(f"\n[ERROR] Could not create sample file: {e}", err=True)
    else:
        click.echo(f"[OK] CSV file found: {csv_path}")

    # Initialize database
    click.echo("\nInitializing database...")
    init_db(clear_existing=False)

    click.echo("\n" + "="*60)
    click.echo("Setup complete! Next steps:")
    click.echo("="*60)
    if not os.path.exists(csv_path):
        click.echo("1. Add your championship data to:")
        click.echo(f"   {csv_path}")
    click.echo("2. Process the data:")
    click.echo("   flask process-data")
    click.echo("3. Run the application:")
    click.echo("   flask run")
    click.echo("="*60)


@click.command('compute-stats')
@with_appcontext
def compute_stats_command() -> None:
    """Pre-compute driver statistics for instant query performance.

    Scans all championship results and computes:
    - Highest position achieved by each driver
    - Best winning margin for each winner
    - Win counts

    This runs once and makes the highest_position endpoint instant.
    """
    import time
    start_time = time.time()

    db = get_db()
    click.echo("Computing driver statistics...")

    # Step 1: Get all unique drivers from a sample championship
    click.echo("  [1/5] Getting driver list...")
    sample_row = db.execute("SELECT standings FROM championship_results LIMIT 1").fetchone()
    if not sample_row:
        click.echo("[ERROR] No championship data found. Run 'flask process-data' first.")
        return

    all_drivers = [d.strip() for d in sample_row['standings'].split(",")]
    click.echo(f"        Found {len(all_drivers)} drivers")

    # Step 2: Get max races
    max_races_row = db.execute("SELECT MAX(num_races) as max_races FROM championship_results").fetchone()
    max_races = max_races_row['max_races']
    click.echo(f"  [2/5] Max season length: {max_races} races")

    # Step 3: Compute highest positions efficiently
    click.echo("  [3/5] Computing highest positions...")
    driver_stats = {}
    drivers_to_find = set(all_drivers)

    for num_races in range(max_races, 0, -1):
        if not drivers_to_find:
            break

        rows = db.execute("""
            SELECT championship_id, standings, num_races
            FROM championship_results
            WHERE num_races = ?
            ORDER BY championship_id DESC
            LIMIT 10000
        """, (num_races,)).fetchall()

        for row in rows:
            championship_id = row['championship_id']
            standings = row['standings']
            championship_num_races = row['num_races']
            drivers_list = [d.strip() for d in standings.split(",")]

            for position, driver in enumerate(drivers_list, start=1):
                if driver not in driver_stats:
                    driver_stats[driver] = {
                        "highest_position": position,
                        "highest_position_max_races": championship_num_races,
                        "highest_position_championship_id": championship_id,
                        "best_margin": None,
                        "best_margin_championship_id": None,
                        "win_count": 0
                    }
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif position < driver_stats[driver]["highest_position"]:
                    driver_stats[driver]["highest_position"] = position
                    driver_stats[driver]["highest_position_max_races"] = championship_num_races
                    driver_stats[driver]["highest_position_championship_id"] = championship_id
                    if position == 1:
                        drivers_to_find.discard(driver)
                elif position == driver_stats[driver]["highest_position"]:
                    if championship_num_races > driver_stats[driver]["highest_position_max_races"]:
                        driver_stats[driver]["highest_position_max_races"] = championship_num_races
                        driver_stats[driver]["highest_position_championship_id"] = championship_id

    click.echo(f"        Computed positions for {len(driver_stats)} drivers")

    # Step 4: Get win counts
    click.echo("  [4/5] Computing win counts...")
    win_counts = db.execute("""
        SELECT winner, COUNT(*) as wins
        FROM championship_results
        WHERE winner IS NOT NULL
        GROUP BY winner
    """).fetchall()

    for row in win_counts:
        if row['winner'] in driver_stats:
            driver_stats[row['winner']]['win_count'] = row['wins']

    # Step 5: Compute best margins (scanning all winner records)
    click.echo("  [5/5] Computing best winning margins...")
    winners = [d for d, data in driver_stats.items() if data["highest_position"] == 1]

    margin_rows = db.execute("""
        SELECT winner, points, championship_id
        FROM championship_results
        WHERE winner IS NOT NULL
    """).fetchall()

    for row in margin_rows:
        winner = row['winner']
        if winner in winners:
            points_str = row['points']
            if points_str:
                points_list = points_str.split(",")
                if len(points_list) >= 2:
                    try:
                        margin = int(points_list[0]) - int(points_list[1])
                        current_best = driver_stats[winner]["best_margin"]
                        if current_best is None or margin > current_best:
                            driver_stats[winner]["best_margin"] = margin
                            driver_stats[winner]["best_margin_championship_id"] = row['championship_id']
                    except ValueError:
                        pass

    # Clear existing stats and insert new ones
    click.echo("  Writing to database...")
    db.execute("DELETE FROM driver_statistics")

    for driver_code, stats in driver_stats.items():
        db.execute("""
            INSERT INTO driver_statistics
            (driver_code, highest_position, highest_position_max_races,
             highest_position_championship_id, best_margin, best_margin_championship_id, win_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            driver_code,
            stats['highest_position'],
            stats['highest_position_max_races'],
            stats['highest_position_championship_id'],
            stats['best_margin'],
            stats['best_margin_championship_id'],
            stats['win_count']
        ))

    db.commit()

    elapsed = time.time() - start_time
    click.echo(f"\n[OK] Driver statistics computed in {elapsed:.1f} seconds")
    click.echo(f"     {len(driver_stats)} drivers processed")

    # Show sample results
    click.echo("\nSample results:")
    for row in db.execute("SELECT * FROM driver_statistics ORDER BY highest_position, win_count DESC LIMIT 5").fetchall():
        margin_str = f"+{row['best_margin']}" if row['best_margin'] else "N/A"
        click.echo(f"  {row['driver_code']}: P{row['highest_position']} ({row['highest_position_max_races']} races), margin: {margin_str}, wins: {row['win_count']}")


def init_app(app: "Flask") -> None:
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)
    app.cli.add_command(setup_command)
    app.cli.add_command(compute_stats_command)
