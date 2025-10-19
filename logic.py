import pandas as pd
import os
from flask import current_app

def get_round_points_for_championship(drivers, round_numbers):
    """
    Gets the points for each driver for each round in a given championship.

    Args:
        drivers (list): A list of driver abbreviations.
        round_numbers (list): A list of round numbers (1-based).

    Returns:
        dict: A dictionary where keys are driver abbreviations and values are
              another dictionary containing 'round_points' (a list of points for each round)
              and 'total_points'.
    """
    csv_path = os.path.join(current_app.config['DATA_FOLDER'], "championships.csv")
    if not os.path.exists(csv_path):
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
