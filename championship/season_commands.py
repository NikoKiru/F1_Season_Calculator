"""CLI commands for managing season-specific race data.

This module provides the `add-race` command to incrementally add race results
to a season, enabling race-by-race tracking during a live F1 season.
"""
import os
import re
import csv
from typing import Dict, List, Tuple

import click
from flask import current_app, Flask
from flask.cli import with_appcontext

from db import get_db, clear_season_data
from .commands import (
    read_csv, generate_race_combinations, calculate_standings,
    save_to_database, save_position_results
)
from .models import get_season_data


def parse_race_results(results_str: str) -> Dict[str, int]:
    """Parse race results from CLI format.

    Args:
        results_str: Comma-separated "DRIVER:POINTS" pairs
                    e.g., "VER:25,NOR:18,LEC:15,PIA:12"

    Returns:
        Dict mapping driver codes to points

    Raises:
        ValueError: If format is invalid
    """
    results = {}
    pairs = results_str.split(',')

    for pair in pairs:
        pair = pair.strip()
        if not pair:
            continue

        if ':' not in pair:
            raise ValueError(f"Invalid format: '{pair}'. Expected 'DRIVER:POINTS'")

        parts = pair.split(':')
        if len(parts) != 2:
            raise ValueError(f"Invalid format: '{pair}'. Expected 'DRIVER:POINTS'")

        driver = parts[0].strip().upper()
        try:
            points = int(parts[1].strip())
        except ValueError:
            raise ValueError(f"Invalid points value: '{parts[1]}' for driver {driver}")

        if not re.match(r'^[A-Z]{3}$', driver):
            raise ValueError(f"Invalid driver code: '{driver}'. Expected 3-letter code")

        results[driver] = points

    return results


def load_season_csv(season: int) -> Tuple[List[str], Dict[str, Dict[int, int]]]:
    """Load existing race data from season CSV file.

    Args:
        season: The season year

    Returns:
        Tuple of (list of drivers, dict mapping driver -> {round: points})
    """
    data_folder = current_app.config['DATA_FOLDER']
    csv_path = os.path.join(data_folder, f'championships_{season}.csv')

    drivers = []
    race_data: Dict[str, Dict[int, int]] = {}

    if not os.path.exists(csv_path):
        return drivers, race_data

    with open(csv_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        header = next(reader)  # First row is header: Driver, 1, 2, 3, ...
        rounds = [int(h) for h in header[1:]]

        for row in reader:
            driver = row[0].strip().upper()
            drivers.append(driver)
            race_data[driver] = {}
            for i, round_num in enumerate(rounds):
                if i + 1 < len(row) and row[i + 1]:
                    try:
                        race_data[driver][round_num] = int(row[i + 1])
                    except ValueError:
                        race_data[driver][round_num] = 0

    return drivers, race_data


def save_season_csv(
    season: int,
    drivers: List[str],
    race_data: Dict[str, Dict[int, int]],
    max_round: int
) -> str:
    """Save race data to season CSV file.

    Args:
        season: The season year
        drivers: List of driver codes in order
        race_data: Dict mapping driver -> {round: points}
        max_round: The highest round number to include

    Returns:
        Path to the saved CSV file
    """
    data_folder = current_app.config['DATA_FOLDER']
    csv_path = os.path.join(data_folder, f'championships_{season}.csv')

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Write header
        header = ['Driver'] + [str(r) for r in range(1, max_round + 1)]
        writer.writerow(header)

        # Write driver data
        for driver in drivers:
            row = [driver]
            for round_num in range(1, max_round + 1):
                points = race_data.get(driver, {}).get(round_num, 0)
                row.append(str(points))
            writer.writerow(row)

    return csv_path


def process_season_data(season: int, csv_path: str, batch_size: int = 100000) -> int:
    """Process championship data for a specific season.

    Similar to commands.process_data but for a specific season.

    Args:
        season: The season year
        csv_path: Path to the CSV file with race data
        batch_size: Number of records to process per batch

    Returns:
        Total number of championship combinations processed
    """
    db = get_db()
    table_name = "championship_results"

    # Read input CSV into NumPy arrays
    drivers, scores = read_csv(csv_path)
    num_races = scores.shape[1]

    click.echo(f"Processing {num_races} races for {len(drivers)} drivers...")

    # Calculate expected combinations
    total_combinations = (2 ** num_races) - 1
    click.echo(f"Expected combinations: {total_combinations:,}")

    # Generate race combinations
    race_combinations_generator = generate_race_combinations(num_races)

    championship_data_batch = []
    standings_batch = []

    # Speed up bulk load
    db.execute("PRAGMA synchronous=OFF;")
    db.execute("PRAGMA journal_mode=WAL;")
    db.execute("BEGIN IMMEDIATE;")

    # Get starting championship_id
    result = db.execute(
        "SELECT COALESCE(MAX(championship_id), 0) FROM championship_results"
    ).fetchone()
    next_championship_id = result[0] + 1

    processed_count = 0

    for i, race_subset in enumerate(race_combinations_generator):
        # Calculate standings
        sorted_drivers, sorted_scores = calculate_standings(drivers, scores, race_subset)

        # Prepare data for database
        winner = sorted_drivers[0]
        standings_str = ','.join(sorted_drivers)
        points_str = ','.join(map(str, sorted_scores))
        rounds_str = ','.join(map(str, [r + 1 for r in race_subset]))
        championship_data_batch.append((len(race_subset), rounds_str, standings_str, winner, points_str))
        standings_batch.append((sorted_drivers, sorted_scores))

        # Save in batches
        if (i + 1) % batch_size == 0:
            save_to_database(db, table_name, championship_data_batch, season=season)

            # Generate and save position_results
            position_data = []
            for j, (drivers_arr, scores_arr) in enumerate(standings_batch):
                champ_id = next_championship_id + j
                for pos, (driver, points) in enumerate(zip(drivers_arr, scores_arr), start=1):
                    position_data.append((champ_id, driver, pos, int(points)))
            save_position_results(db, position_data, season=season)

            click.echo(f"  Processed {i + 1:,} combinations...")
            next_championship_id += len(championship_data_batch)
            championship_data_batch = []
            standings_batch = []

    # Save remaining data
    if championship_data_batch:
        save_to_database(db, table_name, championship_data_batch, season=season)

        position_data = []
        for j, (drivers_arr, scores_arr) in enumerate(standings_batch):
            champ_id = next_championship_id + j
            for pos, (driver, points) in enumerate(zip(drivers_arr, scores_arr), start=1):
                position_data.append((champ_id, driver, pos, int(points)))
        save_position_results(db, position_data, season=season)

        processed_count = i + 1

    # Commit and restore settings
    db.commit()
    db.execute("PRAGMA synchronous=NORMAL;")

    return processed_count


def compute_season_stats(season: int) -> None:
    """Compute driver statistics for a specific season.

    Similar to db.compute_stats but filtered by season.

    Args:
        season: The season year
    """
    import time

    db = get_db()
    start_time = time.time()

    click.echo(f"Computing statistics for season {season}...")

    # Get all drivers from a sample championship for this season
    sample_row = db.execute(
        "SELECT standings FROM championship_results WHERE season = ? LIMIT 1",
        (season,)
    ).fetchone()

    if not sample_row:
        click.echo(f"[WARNING] No championship data found for season {season}")
        return

    all_drivers = [d.strip() for d in sample_row['standings'].split(",")]

    # Get max races for this season
    max_races_row = db.execute(
        "SELECT MAX(num_races) as max_races FROM championship_results WHERE season = ?",
        (season,)
    ).fetchone()
    max_races = max_races_row['max_races']

    click.echo(f"  Found {len(all_drivers)} drivers, max {max_races} races")

    # Compute highest positions
    driver_stats = {}
    drivers_to_find = set(all_drivers)

    for num_races in range(max_races, 0, -1):
        if not drivers_to_find:
            break

        rows = db.execute("""
            SELECT championship_id, standings, num_races
            FROM championship_results
            WHERE num_races = ? AND season = ?
            ORDER BY championship_id DESC
            LIMIT 10000
        """, (num_races, season)).fetchall()

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

    # Get win counts
    win_counts = db.execute("""
        SELECT winner, COUNT(*) as wins
        FROM championship_results
        WHERE winner IS NOT NULL AND season = ?
        GROUP BY winner
    """, (season,)).fetchall()

    for row in win_counts:
        if row['winner'] in driver_stats:
            driver_stats[row['winner']]['win_count'] = row['wins']

    # Compute best margins
    winners = [d for d, data in driver_stats.items() if data["highest_position"] == 1]

    margin_rows = db.execute("""
        SELECT winner, points, championship_id
        FROM championship_results
        WHERE winner IS NOT NULL AND season = ?
    """, (season,)).fetchall()

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

    # Save statistics (replacing existing for this season)
    db.execute("DELETE FROM driver_statistics WHERE season = ?", (season,))

    for driver_code, stats in driver_stats.items():
        db.execute("""
            INSERT INTO driver_statistics
            (driver_code, season, highest_position, highest_position_max_races,
             highest_position_championship_id, best_margin, best_margin_championship_id, win_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            driver_code,
            season,
            stats['highest_position'],
            stats['highest_position_max_races'],
            stats['highest_position_championship_id'],
            stats['best_margin'],
            stats['best_margin_championship_id'],
            stats['win_count']
        ))

    # Compute win probability cache
    db.execute("DELETE FROM win_probability_cache WHERE season = ?", (season,))

    wins_per_length = db.execute("""
        SELECT winner, num_races, COUNT(*) as wins
        FROM championship_results
        WHERE winner IS NOT NULL AND season = ?
        GROUP BY winner, num_races
    """, (season,)).fetchall()

    totals_per_length = db.execute("""
        SELECT num_races, COUNT(*) as total
        FROM championship_results
        WHERE season = ?
        GROUP BY num_races
    """, (season,)).fetchall()

    totals_dict = {row['num_races']: row['total'] for row in totals_per_length}

    cache_data = []
    for row in wins_per_length:
        driver = row['winner']
        num_races = row['num_races']
        wins = row['wins']
        total = totals_dict.get(num_races, 0)
        cache_data.append((driver, num_races, wins, total, season))

    existing_combinations = {(d, n) for d, n, _, _, _ in cache_data}
    for driver in all_drivers:
        for num_races, total in totals_dict.items():
            if (driver, num_races) not in existing_combinations:
                cache_data.append((driver, num_races, 0, total, season))

    db.executemany("""
        INSERT INTO win_probability_cache (driver_code, num_races, win_count, total_at_length, season)
        VALUES (?, ?, ?, ?, ?)
    """, cache_data)

    db.commit()

    elapsed = time.time() - start_time
    click.echo(f"[OK] Statistics computed in {elapsed:.1f}s ({len(driver_stats)} drivers)")


@click.command('add-race')
@click.option('--season', type=int, required=True, help='Season year (e.g., 2026)')
@click.option('--race', 'race_num', type=int, required=True, help='Race number (1-24)')
@click.option('--results', type=str, required=True,
              help='Race results as "DRIVER:POINTS,..." (e.g., "VER:25,NOR:18,LEC:15")')
@click.option('--skip-reprocess', is_flag=True, help='Skip reprocessing (just update CSV)')
@with_appcontext
def add_race_command(season: int, race_num: int, results: str, skip_reprocess: bool) -> None:
    """Add race results for a season and reprocess championship combinations.

    Example:
        flask add-race --season 2026 --race 1 --results "VER:25,NOR:18,LEC:15,PIA:12"

    This command:
    1. Parses the race results
    2. Updates/creates the season CSV file
    3. Clears existing season data from database
    4. Reprocesses all championship combinations
    5. Recomputes driver statistics
    """
    import time
    start_time = time.time()

    # Validate race number
    if race_num < 1 or race_num > 24:
        click.echo(f"[ERROR] Invalid race number: {race_num}. Must be 1-24.", err=True)
        return

    # Parse race results
    try:
        race_results = parse_race_results(results)
    except ValueError as e:
        click.echo(f"[ERROR] {e}", err=True)
        return

    if not race_results:
        click.echo("[ERROR] No valid race results provided.", err=True)
        return

    click.echo(f"\nAdding Race {race_num} results for season {season}")
    click.echo(f"Results: {race_results}")

    # Load existing season data
    drivers, race_data = load_season_csv(season)

    # Get season config for driver list
    try:
        season_data = get_season_data(season)
        config_drivers = list(season_data.drivers.keys())
    except FileNotFoundError:
        click.echo(f"[ERROR] Season config not found for {season}. Create data/seasons/{season}.json first.", err=True)
        return

    # If no existing data, use config drivers
    if not drivers:
        drivers = config_drivers
        race_data = {d: {} for d in drivers}
        click.echo(f"  Creating new season data with {len(drivers)} drivers from config")
    else:
        max_race = max(max(race_data[d].keys(), default=0) for d in drivers)
        click.echo(f"  Loaded existing data: {len(drivers)} drivers, {max_race} races")

    # Update race data
    for driver, points in race_results.items():
        if driver in race_data:
            race_data[driver][race_num] = points
        else:
            click.echo(f"  [WARNING] Driver {driver} not in season, adding with 0 for other races")
            drivers.append(driver)
            race_data[driver] = {race_num: points}

    # Ensure all drivers have 0 points for this race if not specified
    for driver in drivers:
        if race_num not in race_data.get(driver, {}):
            if driver not in race_data:
                race_data[driver] = {}
            race_data[driver][race_num] = 0

    # Save updated CSV
    max_round = max(max(race_data[d].keys(), default=0) for d in drivers)
    csv_path = save_season_csv(season, drivers, race_data, max_round)
    click.echo(f"  Saved to: {csv_path}")

    if skip_reprocess:
        click.echo("\n[OK] CSV updated. Skipping reprocess as requested.")
        return

    # Clear existing season data
    click.echo(f"\nClearing existing data for season {season}...")
    clear_season_data(season)

    # Reprocess championship combinations
    click.echo("\nProcessing championship combinations...")
    total_processed = process_season_data(season, csv_path)
    click.echo(f"  Processed {total_processed:,} combinations")

    # Recompute statistics
    click.echo("\nComputing statistics...")
    compute_season_stats(season)

    elapsed = time.time() - start_time
    click.echo(f"\n[OK] Race {race_num} added to season {season} in {elapsed:.1f}s")


@click.command('clear-season')
@click.option('--season', type=int, required=True, help='Season year to clear')
@click.option('--confirm', is_flag=True, help='Confirm deletion without prompting')
@with_appcontext
def clear_season_command(season: int, confirm: bool) -> None:
    """Clear all data for a specific season from the database.

    Example:
        flask clear-season --season 2026 --confirm
    """
    if not confirm:
        click.confirm(
            f"This will delete ALL data for season {season}. Continue?",
            abort=True
        )

    deleted = clear_season_data(season)
    click.echo(f"[OK] Cleared {deleted:,} records for season {season}")


@click.command('add-races-batch')
@click.option('--season', type=int, required=True, help='Season year (e.g., 2026)')
@click.option('--csv', 'csv_path', type=click.Path(exists=True), required=True,
              help='Path to CSV file with race data (same format as championships.csv)')
@click.option('--skip-reprocess', is_flag=True, help='Skip reprocessing (just import CSV)')
@with_appcontext
def add_races_batch_command(season: int, csv_path: str, skip_reprocess: bool) -> None:
    """Import multiple races from a CSV file for a season.

    The CSV should use the standard championships.csv format:
        Driver,1,2,3,...
        VER,25,18,25,...
        NOR,18,25,18,...

    This command merges the CSV data into the season's existing data,
    then reprocesses all championship combinations.

    Example:
        flask add-races-batch --season 2026 --csv path/to/races.csv
    """
    import time
    start_time = time.time()

    # Validate season config exists
    try:
        season_data = get_season_data(season)
    except FileNotFoundError:
        click.echo(f"[ERROR] Season config not found for {season}. "
                   f"Create data/seasons/{season}.json first.", err=True)
        return

    # Read the input CSV
    click.echo(f"\nImporting race data for season {season} from: {csv_path}")

    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
    except Exception as e:
        click.echo(f"[ERROR] Could not read CSV: {e}", err=True)
        return

    if 'Driver' not in df.columns:
        click.echo("[ERROR] CSV must have a 'Driver' column.", err=True)
        return

    race_cols = [col for col in df.columns if col != 'Driver']
    if not race_cols:
        click.echo("[ERROR] CSV has no race columns.", err=True)
        return

    click.echo(f"  Found {len(df)} drivers, {len(race_cols)} races in CSV")

    # Load existing season data
    existing_drivers, existing_data = load_season_csv(season)

    # Merge: input CSV overwrites existing data for matching races
    config_drivers = list(season_data.drivers.keys())
    all_drivers = list(dict.fromkeys(config_drivers + existing_drivers))  # preserve order, dedupe

    merged_data: Dict[str, Dict[int, int]] = {d: {} for d in all_drivers}

    # Copy existing data
    for driver in all_drivers:
        if driver in existing_data:
            merged_data[driver].update(existing_data[driver])

    # Overlay new CSV data
    for _, row in df.iterrows():
        driver = str(row['Driver']).strip().upper()
        if driver not in merged_data:
            all_drivers.append(driver)
            merged_data[driver] = {}
        for col in race_cols:
            try:
                round_num = int(col)
                points = int(row[col]) if pd.notna(row[col]) else 0
                merged_data[driver][round_num] = points
            except (ValueError, TypeError):
                continue

    # Determine max round
    max_round = 0
    for d in all_drivers:
        if merged_data[d]:
            max_round = max(max_round, max(merged_data[d].keys()))

    if max_round == 0:
        click.echo("[ERROR] No valid race data found.", err=True)
        return

    # Ensure all drivers have 0 for missing races
    for driver in all_drivers:
        for r in range(1, max_round + 1):
            if r not in merged_data[driver]:
                merged_data[driver][r] = 0

    # Save merged CSV
    csv_out = save_season_csv(season, all_drivers, merged_data, max_round)
    click.echo(f"  Saved merged data to: {csv_out}")
    click.echo(f"  {len(all_drivers)} drivers, {max_round} races")

    if skip_reprocess:
        click.echo("\n[OK] CSV imported. Skipping reprocess as requested.")
        return

    # Clear and reprocess
    click.echo(f"\nClearing existing data for season {season}...")
    clear_season_data(season)

    click.echo("\nProcessing championship combinations...")
    total_processed = process_season_data(season, csv_out)
    click.echo(f"  Processed {total_processed:,} combinations")

    click.echo("\nComputing statistics...")
    compute_season_stats(season)

    elapsed = time.time() - start_time
    click.echo(f"\n[OK] Batch import complete for season {season} in {elapsed:.1f}s")


@click.command('season-status')
@click.option('--season', type=int, default=None,
              help='Season year to check. If not specified, shows all seasons.')
@with_appcontext
def season_status_command(season: int) -> None:
    """Show the current state of a season's data.

    Displays which races have data, how many combinations are processed,
    and whether statistics have been computed.

    Example:
        flask season-status --season 2026
        flask season-status
    """
    from db import get_db
    from .models import get_available_seasons
    from .models import DEFAULT_SEASON as _default_season

    db = get_db()

    if season is not None:
        seasons_to_check = [season]
    else:
        seasons_to_check = get_available_seasons()
        if not seasons_to_check:
            click.echo("No season configurations found.")
            return

    for s in seasons_to_check:
        click.echo(f"\n{'='*50}")
        click.echo(f"Season {s}" + (" (default)" if s == _default_season else ""))
        click.echo(f"{'='*50}")

        # Check season config
        try:
            season_data = get_season_data(s)
            click.echo(f"  Config: {len(season_data.drivers)} drivers, "
                       f"{len(season_data.round_names)} rounds")
        except FileNotFoundError:
            click.echo(f"  Config: NOT FOUND (data/seasons/{s}.json)")
            continue

        # Check CSV data
        data_folder = current_app.config['DATA_FOLDER']
        season_csv = os.path.join(data_folder, f'championships_{s}.csv')
        if os.path.exists(season_csv):
            drivers, race_data = load_season_csv(s)
            races_with_data = set()
            for d in drivers:
                for r, pts in race_data.get(d, {}).items():
                    if pts > 0:
                        races_with_data.add(r)
            race_list = sorted(races_with_data)
            race_names = [season_data.round_names.get(r, str(r)) for r in race_list]
            click.echo(f"  CSV: {len(drivers)} drivers, {len(race_list)} races with data")
            if race_names:
                click.echo(f"  Races: {', '.join(race_names)}")
        else:
            # Check generic CSV
            generic_csv = os.path.join(data_folder, 'championships.csv')
            if os.path.exists(generic_csv):
                click.echo("  CSV: Using generic championships.csv")
            else:
                click.echo("  CSV: No data file found")

        # Check database records
        count_row = db.execute(
            "SELECT COUNT(*) as cnt FROM championship_results WHERE season = ?",
            (s,)
        ).fetchone()
        record_count = count_row['cnt'] if count_row else 0

        if record_count > 0:
            max_races_row = db.execute(
                "SELECT MAX(num_races) as max_races, MIN(num_races) as min_races "
                "FROM championship_results WHERE season = ?",
                (s,)
            ).fetchone()
            click.echo(f"  Database: {record_count:,} championship combinations")
            click.echo(f"  Race range: {max_races_row['min_races']}-{max_races_row['max_races']} races")
        else:
            click.echo("  Database: No processed data")

        # Check statistics
        stats_row = db.execute(
            "SELECT COUNT(*) as cnt FROM driver_statistics WHERE season = ?",
            (s,)
        ).fetchone()
        stats_count = stats_row['cnt'] if stats_row else 0

        prob_row = db.execute(
            "SELECT COUNT(*) as cnt FROM win_probability_cache WHERE season = ?",
            (s,)
        ).fetchone()
        prob_count = prob_row['cnt'] if prob_row else 0

        if stats_count > 0:
            click.echo(f"  Statistics: {stats_count} driver stats, {prob_count} probability entries")
        else:
            click.echo("  Statistics: Not computed")

    click.echo("")


def init_app(app: Flask) -> None:
    """Register season management CLI commands."""
    app.cli.add_command(add_race_command)
    app.cli.add_command(clear_season_command)
    app.cli.add_command(add_races_batch_command)
    app.cli.add_command(season_status_command)
