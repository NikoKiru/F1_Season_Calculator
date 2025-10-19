from flask import (
    Blueprint, jsonify, request
)
from .db import get_db
from .rounds import ROUND_NAMES_2025
from .drivers import DRIVER_NAMES
from .logic import get_round_points_for_championship

bp = Blueprint('api', __name__, url_prefix='/api')

# Function to query all data from the SQLite database
def get_all_data():
    db = get_db()
    # Replace `table_name` with the actual name of your table
    table_name = 'championship_results'

    # Fetch all data from the table
    rows = db.execute(f"SELECT * FROM {table_name}").fetchall()

    # Format data as a list of dictionaries
    data = []
    for row in rows:
        championship_data = dict(row)
        if championship_data.get('rounds'):
            round_numbers = [int(r) for r in championship_data['rounds'].split(',')]
            round_names = [ROUND_NAMES_2025.get(r, 'Unknown') for r in round_numbers]
            championship_data['round_names'] = round_names
        if championship_data.get('standings') and championship_data.get('points'):
            drivers = championship_data['standings'].split(',')
            points = [int(p) for p in championship_data['points'].split(',')]
            championship_data['driver_points'] = dict(zip(drivers, points))
            championship_data['driver_names'] = {driver: DRIVER_NAMES.get(driver, 'Unknown') for driver in drivers}
        data.append(championship_data)
    return data

# Flask route to return all data as JSON
@bp.route('/data', methods=['GET'])
def get_data_route():
    """
    Fetch All Championship Data
    This endpoint retrieves all championship results stored in the database.
    ---
    responses:
      200:
        description: A list of all championship results.
    """
    data = get_all_data()
    return jsonify(data)

@bp.route('/championship/<int:id>', methods=['GET'])
def get_championship(id):
    """
    Fetch a Specific Championship by ID
    This endpoint retrieves a single championship result by its unique ID.
    ---
    parameters:
      - name: id
        in: path
        type: integer
        required: true
        description: The unique ID of the championship to retrieve.
    responses:
      200:
        description: The championship data.
      404:
        description: Championship not found.
    """
    db = get_db()
    row = db.execute(f"SELECT * FROM championship_results WHERE championship_id = ?", (id,)).fetchone()

    if row:
        championship_data = dict(row)
        if championship_data.get('rounds'):
            round_numbers = [int(r) for r in championship_data['rounds'].split(',')]
            round_names = [ROUND_NAMES_2025.get(r, 'Unknown') for r in round_numbers]
            championship_data['round_names'] = round_names
        if championship_data.get('standings') and championship_data.get('points'):
            drivers = championship_data['standings'].split(',')
            points = [int(p) for p in championship_data['points'].split(',')]
            championship_data['driver_points'] = dict(zip(drivers, points))
            championship_data['driver_names'] = {driver: DRIVER_NAMES.get(driver, 'Unknown') for driver in drivers}
            
            # Get round-by-round points
            if championship_data.get('rounds'):
                round_numbers = [int(r) for r in championship_data['rounds'].split(',')]
                round_points_data = get_round_points_for_championship(drivers, round_numbers)
                championship_data['round_points_data'] = round_points_data

        return jsonify(championship_data)
    else:
        return jsonify({"error": "Championship not found"}), 404



@bp.route('/all_championship_wins', methods=['GET'])
def all_championship_wins():
    """
    Get All Championship Wins for All Drivers
    This endpoint returns a summary of championship wins for every driver.
    ---
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are their total wins.
    """
    db = get_db()

    table_name = 'championship_results'

    # Query to group by the indexed 'winner' column
    query = f"""
        SELECT winner, COUNT(*) as wins
        FROM {table_name}
        GROUP BY winner
        ORDER BY wins DESC
    """
    
    rows = db.execute(query).fetchall()

    # Format as a dictionary
    championship_wins = {row['winner']: row['wins'] for row in rows}

    return jsonify(championship_wins)



@bp.route('/largest_championship_wins', methods=['GET'])
def largest_championship_wins():
    """
    Find Championships Won by a Driver with a Specific Number of Races
    This endpoint returns the IDs of championships won by a specific driver in seasons with a given number of races.
    ---
    parameters:
      - name: driver
        in: query
        type: string
        required: true
        description: The abbreviation of the driver.
      - name: num_races
        in: query
        type: integer
        required: true
        description: The number of races in the championship.
    responses:
      200:
        description: A list of championship IDs matching the criteria.
      400:
        description: Missing required query parameters.
    """
    # Get query parameters
    driver = request.args.get('driver')  # Driver abbreviation
    num_races = request.args.get('num_races', type=int)  # Number of races

    if not driver or not num_races:
        return jsonify({"error": "Please provide both 'driver' and 'num_races' as query parameters"}), 400

    db = get_db()

    table_name = 'championship_results'
    championship_id_column = 'championship_id'

    # Query using the indexed 'winner' and 'num_races' columns
    query = f"""
        SELECT {championship_id_column}
        FROM {table_name}
        WHERE num_races = ? AND winner = ?
    """
    rows = db.execute(query, (num_races, driver.upper())).fetchall()

    # Extract championship IDs
    matching_championships = [row[championship_id_column] for row in rows]

    # Return the matching championship IDs
    return jsonify({driver: matching_championships})

@bp.route('/highest_position', methods=['GET'])
def highest_position():
    """
    Get the Highest Championship Position for Each Driver
    This endpoint returns the best final championship ranking for every driver, including up to the 5 largest championship IDs where this rank was achieved.
    ---
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are objects containing their highest rank and a list of up to 5 corresponding championship IDs.
    """
    db = get_db()

    table_name = 'championship_results'
    standings_column = 'standings'
    championship_id_column = 'championship_id'

    # Query to fetch all standings, ordered by championship_id descending to process largest IDs first
    query = f"SELECT {championship_id_column}, {standings_column} FROM {table_name} ORDER BY {championship_id_column} DESC"
    rows = db.execute(query).fetchall()

    highest_positions = {}

    for row in rows:
        championship_id = row[championship_id_column]
        standings = row[standings_column]
        drivers = [driver.strip() for driver in standings.split(",")]

        for position, driver in enumerate(drivers, start=1):
            if driver not in highest_positions:
                highest_positions[driver] = {"position": position, "championship_ids": [championship_id]}
            elif position < highest_positions[driver]["position"]:
                highest_positions[driver] = {"position": position, "championship_ids": [championship_id]}
            elif position == highest_positions[driver]["position"]:
                if len(highest_positions[driver]["championship_ids"]) < 5:
                    highest_positions[driver]["championship_ids"].append(championship_id)

    return jsonify(highest_positions)


@bp.route('/head_to_head/<string:driver1>/<string:driver2>', methods=['GET'])
def head_to_head(driver1, driver2):
    """
    Head-to-Head Driver Comparison
    Compares two drivers to see who finished ahead more often across all championship scenarios.
    ---
    parameters:
      - name: driver1
        in: path
        type: string
        required: true
        description: The abbreviation for the first driver.
      - name: driver2
        in: path
        type: string
        required: true
        description: The abbreviation for the second driver.
    responses:
      200:
        description: A JSON object showing the win count for each driver in the head-to-head comparison.
    """
    db = get_db()

    d1 = driver1.upper()
    d2 = driver2.upper()

    # This query is complex. It adds commas to the start and end of the standings string
    # to safely find the position of a driver's abbreviation.
    query = f"""
        SELECT
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',') < INSTR(',' || standings || ',', ',' || ? || ',') THEN 1 ELSE 0 END) as driver1_wins,
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',') > INSTR(',' || standings || ',', ',' || ? || ',') THEN 1 ELSE 0 END) as driver2_wins
        FROM championship_results
        WHERE INSTR(standings, ?) > 0 AND INSTR(standings, ?) > 0;
    """
    result = db.execute(query, (d1, d2, d1, d2, d1, d2)).fetchone()
    
    return jsonify({
        d1: result['driver1_wins'],
        d2: result['driver2_wins']
    })

@bp.route('/min_races_to_win', methods=['GET'])
def min_races_to_win():
    """
    Minimum Races Needed for a Driver to Win a Championship
    Calculates the smallest number of races a driver needed to win a championship.
    ---
    responses:
      200:
        description: The minimum number of races for a championship win for each driver.
    """
    db = get_db()

    query = "SELECT winner, MIN(num_races) as min_races FROM championship_results WHERE winner IS NOT NULL GROUP BY winner ORDER BY min_races ASC"
    results = db.execute(query).fetchall()

    data = {row['winner']: row['min_races'] for row in results}
    
    return jsonify(data)

@bp.route('/most_common_runner_up', methods=['GET'])
def most_common_runner_up():
    """
    Most Common Championship Runner-Up
    Counts how many times each driver finished in second place across all scenarios.
    ---
    responses:
      200:
        description: A JSON object with drivers and their count of second-place finishes.
    """
    db = get_db()

    # This query extracts the second driver from the comma-separated standings string.
    query = """
        SELECT
            SUBSTR(
                SUBSTR(standings, INSTR(standings, ',') + 1),
                1,
                INSTR(SUBSTR(standings, INSTR(standings, ',') + 1), ',') - 1
            ) as runner_up,
            COUNT(*) as second_place_finishes
        FROM championship_results
        GROUP BY runner_up
        ORDER BY second_place_finishes DESC;
    """
    rows = db.execute(query).fetchall()

    runner_up_counts = {row['runner_up']: row['second_place_finishes'] for row in rows if row['runner_up']}

    return jsonify(runner_up_counts)

@bp.route('/championship_win_probability', methods=['GET'])
def championship_win_probability():
    """
    Calculate the probability of winning a championship for each driver based on season length.
    ---
    responses:
      200:
        description: A JSON object with win probabilities for each driver.
    """
    db = get_db()
    
    # Get total wins for each driver
    query_wins = "SELECT winner, COUNT(*) as wins FROM championship_results GROUP BY winner"
    driver_total_wins = {row['winner']: row['wins'] for row in db.execute(query_wins).fetchall()}

    # Get wins per season length for each driver
    query_wins_per_length = "SELECT winner, num_races, COUNT(*) as wins FROM championship_results GROUP BY winner, num_races"
    wins_per_length = {}
    for row in db.execute(query_wins_per_length).fetchall():
        if row['winner'] not in wins_per_length:
            wins_per_length[row['winner']] = {}
        wins_per_length[row['winner']][row['num_races']] = row['wins']

    # Get total seasons per length
    query_seasons_per_length = "SELECT num_races, COUNT(*) as total FROM championship_results GROUP BY num_races"
    seasons_per_length = {row['num_races']: row['total'] for row in db.execute(query_seasons_per_length).fetchall()}
    
    season_lengths = sorted(seasons_per_length.keys())

    drivers = sorted(driver_total_wins.keys(), key=lambda d: driver_total_wins[d], reverse=True)

    driver_data = []
    for driver in drivers:
        data = {
            "driver": driver,
            "total_titles": driver_total_wins.get(driver, 0),
            "wins_per_length": [wins_per_length.get(driver, {}).get(length, 0) for length in season_lengths],
            "percentages": []
        }
        for length in season_lengths:
            wins = wins_per_length.get(driver, {}).get(length, 0)
            total_seasons = seasons_per_length.get(length, 1)
            percentage = (wins / total_seasons) * 100 if total_seasons > 0 else 0
            data["percentages"].append(round(percentage, 2))
        driver_data.append(data)

    response_data = {
        "season_lengths": season_lengths,
        "possible_seasons": [seasons_per_length.get(l, 0) for l in season_lengths],
        "drivers_data": driver_data,
        "driver_names": DRIVER_NAMES
    }

    return jsonify(response_data)
