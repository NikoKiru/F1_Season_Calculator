import pandas as pd
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

    df = pd.read_csv(csv_path)
    df = df.set_index('Driver')

    # Convert round numbers to 0-based index for DataFrame lookup
    # The round numbers in round_numbers are 1-based, and correspond to column names '1', '2', etc.
    round_cols = [str(r) for r in round_numbers]

    championship_points = {}
    for driver in drivers:
        if driver in df.index:
            # Ensure all round columns exist in the DataFrame
            existing_round_cols = [col for col in round_cols if col in df.columns]
            round_points = df.loc[driver, existing_round_cols].tolist()
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

    df = pd.read_csv(csv_path)

    round_cols = [str(r) for r in round_numbers]

    # Ensure all requested round columns exist
    existing_round_cols = [col for col in round_cols if col in df.columns]
    if not existing_round_cols:
        return {}

    # Sum points for selected rounds for each driver
    df['total_points'] = df[existing_round_cols].sum(axis=1)

    # Sort by total points descending
    standings_df = df.sort_values(by='total_points', ascending=False)

    # Get standings, points, and winner
    standings = standings_df['Driver'].tolist()
    points = standings_df['total_points'].astype(int).tolist()
    winner = standings[0] if standings else None

    return {
        'standings': standings,
        'points': points,
        'winner': winner
    }
