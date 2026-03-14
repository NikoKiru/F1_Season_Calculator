import csv
import os
from typing import Dict, List, Any, Optional
from flask import current_app

from .models import DEFAULT_SEASON


def _get_csv_path(season: Optional[int] = None) -> Optional[str]:
    """Get the CSV path for a season, trying season-specific file first.

    Args:
        season: The season year. Defaults to DEFAULT_SEASON.

    Returns:
        Path to the CSV file, or None if no file exists.
    """
    if season is None:
        season = DEFAULT_SEASON

    data_folder = current_app.config['DATA_FOLDER']

    # Try season-specific CSV first
    season_csv = os.path.join(data_folder, f"championships_{season}.csv")
    if os.path.exists(season_csv):
        return season_csv

    # Fall back to generic championships.csv
    generic_csv = os.path.join(data_folder, "championships.csv")
    if os.path.exists(generic_csv):
        return generic_csv

    return None


def _read_csv_data(csv_path: str) -> tuple[dict[str, dict[str, int]], list[str]]:
    """Read CSV and return driver points data and column names.

    Args:
        csv_path: Path to the CSV file.

    Returns:
        Tuple of (driver_data dict mapping driver -> {round_col: points}, round_columns list)
    """
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        round_columns = [c for c in columns if c != 'Driver']
        driver_data = {}
        for row in reader:
            driver = row['Driver']
            driver_data[driver] = {
                col: int(row[col]) for col in round_columns
            }
    return driver_data, round_columns


def get_round_points_for_championship(
    drivers: List[str],
    round_numbers: List[int],
    season: Optional[int] = None
) -> Dict[str, Dict[str, Any]]:
    """
    Gets the points for each driver for each round in a given championship.

    Args:
        drivers (list): A list of driver abbreviations.
        round_numbers (list): A list of round numbers (1-based).
        season (int, optional): The season year. Defaults to DEFAULT_SEASON.

    Returns:
        dict: A dictionary where keys are driver abbreviations and values are
              another dictionary containing 'round_points' (a list of points for each round)
              and 'total_points'.
    """
    csv_path = _get_csv_path(season)
    if csv_path is None:
        return {}

    driver_data, available_columns = _read_csv_data(csv_path)
    round_cols = [str(r) for r in round_numbers]

    championship_points = {}
    for driver in drivers:
        if driver in driver_data:
            existing_round_cols = [col for col in round_cols if col in available_columns]
            round_points = [driver_data[driver][col] for col in existing_round_cols]
            total_points = sum(round_points)
            championship_points[driver] = {
                'round_points': round_points,
                'total_points': total_points
            }
    return championship_points


def calculate_championship_from_rounds(
    round_numbers: List[int],
    season: Optional[int] = None
) -> Dict[str, Any]:
    """
    Calculates championship standings from a given list of round numbers.

    Args:
        round_numbers (list): A list of round numbers (1-based).
        season (int, optional): The season year. Defaults to DEFAULT_SEASON.

    Returns:
        dict: A dictionary containing 'standings', 'points', and 'winner'.
    """
    csv_path = _get_csv_path(season)
    if csv_path is None:
        return {}

    driver_data, available_columns = _read_csv_data(csv_path)
    round_cols = [str(r) for r in round_numbers]

    existing_round_cols = [col for col in round_cols if col in available_columns]
    if not existing_round_cols:
        return {}

    # Calculate total points for each driver
    totals = []
    for driver, points in driver_data.items():
        total = sum(points[col] for col in existing_round_cols)
        totals.append((driver, total))

    # Sort by total points descending
    totals.sort(key=lambda x: x[1], reverse=True)

    standings = [t[0] for t in totals]
    points = [t[1] for t in totals]
    winner = standings[0] if standings else None

    return {
        'standings': standings,
        'points': points,
        'winner': winner
    }
