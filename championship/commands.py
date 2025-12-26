import os
import itertools
import sqlite3
from typing import Tuple, List, Iterator

import click
import numpy as np
import pandas as pd
from flask import current_app, Flask
from flask.cli import with_appcontext

# Root-level module (absolute import - db.py is at project root)
from db import get_db


# Step 1: Read the CSV file and convert to NumPy for performance
def read_csv(file_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Read championship CSV and return drivers and numeric score array.

    Ensures driver abbreviations are strings (uppercased, stripped) and
    score columns are numeric integers (NaN -> 0).
    """
    df = pd.read_csv(file_path)
    # Driver column (first column)
    drivers = df.iloc[:, 0].astype(str).str.strip().str.upper().to_numpy()
    # Scores: coerce non-numeric to NaN, then fill with 0 and cast to int
    scores_df = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce').fillna(0).astype(int)
    scores = scores_df.to_numpy()
    return drivers, scores


# Step 2: Generate subsets of races
def generate_race_combinations(num_races: int) -> Iterator[Tuple[int, ...]]:
    for r in range(1, num_races + 1):
        for combination in itertools.combinations(range(num_races), r):  # Use 0-based index
            yield combination


# Step 3: Calculate championship standings using NumPy
def calculate_standings(
    drivers: np.ndarray,
    scores: np.ndarray,
    race_subset: Tuple[int, ...]
) -> Tuple[np.ndarray, np.ndarray]:
    # Sum scores for the given subset of races. This is much faster in NumPy.
    subset_scores = scores[:, race_subset].sum(axis=1)

    # Sort drivers based on scores
    sorted_indices = np.argsort(-subset_scores)  # Sort in descending order
    sorted_drivers = drivers[sorted_indices]
    sorted_scores = subset_scores[sorted_indices]

    return sorted_drivers, sorted_scores


# Step 4: Save to SQLite database
def save_to_database(
    db: sqlite3.Connection,
    table_name: str,
    championship_data: List[Tuple[int, str, str, str, str]]
) -> None:
    """Insert a batch of championship rows into the database.

    Uses a single executemany call for efficiency.
    """
    if not championship_data:
        return

    db.executemany(
        f"""
    INSERT INTO {table_name} (num_races, rounds, standings, winner, points)
    VALUES (?, ?, ?, ?, ?);
    """,
        championship_data,
    )
    # Commit handled by caller for larger transactional control


def save_position_results(
    db: sqlite3.Connection,
    position_data: List[Tuple[int, str, int, int]]
) -> None:
    """Insert a batch of position results into the database.

    Each entry maps a championship_id to a driver's position and points.
    """
    if not position_data:
        return

    db.executemany(
        """
    INSERT INTO position_results (championship_id, driver_code, position, points)
    VALUES (?, ?, ?, ?);
    """,
        position_data,
    )


# Main function
def process_data(batch_size: int = 100000) -> None:
    """Processes the championship data and saves it to the database."""
    db = get_db()
    table_name = "championship_results"
    csv_path = os.path.join(current_app.config['DATA_FOLDER'], "championships.csv")
    if not os.path.exists(csv_path):
        click.echo(f"CSV file not found: {csv_path}")
        return

    # Step 1: Read input CSV into NumPy arrays
    drivers, scores = read_csv(csv_path)
    num_races = scores.shape[1]

    # Step 2: Get a generator for race combinations
    race_combinations_generator = generate_race_combinations(num_races)

    championship_data_batch = []
    # Store (sorted_drivers, sorted_scores) for position_results generation
    standings_batch = []

    # Speed up bulk load: relax durability during import, wrap in a single transaction
    db.execute("PRAGMA synchronous=OFF;")
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("BEGIN IMMEDIATE;")

    # Get starting championship_id for position_results mapping
    result = db.execute("SELECT COALESCE(MAX(championship_id), 0) FROM championship_results").fetchone()
    next_championship_id = result[0] + 1

    # Step 3: Process each combination
    for i, race_subset in enumerate(race_combinations_generator):
        # Calculate standings using the optimized NumPy function
        sorted_drivers, sorted_scores = calculate_standings(drivers, scores, race_subset)

        # Prepare data for database
        winner = sorted_drivers[0]
        standings_str = ','.join(sorted_drivers)
        points_str = ','.join(map(str, sorted_scores))
        # Add 1 to race indices for rounds string to be 1-based
        rounds_str = ','.join(map(str, [r + 1 for r in race_subset]))
        championship_data_batch.append((len(race_subset), rounds_str, standings_str, winner, points_str))
        standings_batch.append((sorted_drivers, sorted_scores))

        # Step 4: Save to database in batches
        if (i + 1) % batch_size == 0:
            save_to_database(db, table_name, championship_data_batch)

            # Generate and save position_results for this batch
            position_data = []
            for j, (drivers_arr, scores_arr) in enumerate(standings_batch):
                champ_id = next_championship_id + j
                for pos, (driver, points) in enumerate(zip(drivers_arr, scores_arr), start=1):
                    position_data.append((champ_id, driver, pos, int(points)))
            save_position_results(db, position_data)

            click.echo(f"Processed batch through combination {i + 1}...")
            next_championship_id += len(championship_data_batch)
            championship_data_batch = []
            standings_batch = []

    # Save any remaining data
    if championship_data_batch:
        save_to_database(db, table_name, championship_data_batch)

        # Generate and save position_results for final batch
        position_data = []
        for j, (drivers_arr, scores_arr) in enumerate(standings_batch):
            champ_id = next_championship_id + j
            for pos, (driver, points) in enumerate(zip(drivers_arr, scores_arr), start=1):
                position_data.append((champ_id, driver, pos, int(points)))
        save_position_results(db, position_data)

        click.echo(f"Processed final batch of {len(championship_data_batch)} combinations.")

    # Commit the entire import and restore safer settings
    db.commit()
    db.execute("PRAGMA synchronous=NORMAL;")
    click.echo(f"All data saved to database, table: {table_name}")


@click.command('process-data')
@click.option('--batch-size', default=100000, type=int, help='Number of records to process per batch')
@with_appcontext
def process_data_command(batch_size: int) -> None:
    """Processes championship data and saves it to the database.

    Reads championships.csv from the data folder and generates all possible
    championship combinations, saving them to the database.
    """
    # Validate that CSV exists
    csv_path = os.path.join(current_app.config['DATA_FOLDER'], "championships.csv")
    if not os.path.exists(csv_path):
        click.echo(f"[ERROR] CSV file not found at {csv_path}", err=True)
        click.echo("\nPlease run 'flask setup' first to create the necessary folders.", err=True)
        return

    click.echo(f"Processing data from: {csv_path}")
    click.echo(f"Batch size: {batch_size:,}")

    try:
        process_data(batch_size=batch_size)
        click.echo('[OK] Successfully processed and saved data to database.')
    except Exception as e:
        click.echo(f'[ERROR] Error processing data: {e}', err=True)
        raise


def init_app(app: Flask) -> None:
    app.cli.add_command(process_data_command)
