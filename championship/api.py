from flask import (
    Blueprint, jsonify, request, redirect, url_for
)
# Import db module - works with both package and standalone setup
try:
    from ..db import get_db
except ImportError:
    import db
    get_db = db.get_db

try:
    from .models import ROUND_NAMES_2025, DRIVER_NAMES
    from .logic import get_round_points_for_championship, calculate_championship_from_rounds
except ImportError:
    from championship.models import ROUND_NAMES_2025, DRIVER_NAMES
    from championship.logic import get_round_points_for_championship, calculate_championship_from_rounds

bp = Blueprint('api', __name__, url_prefix='/api')

def format_championship_data(row, with_round_points=False):
    """Formats a championship row from the database into a dictionary."""
    if not row:
        return None

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

        if with_round_points and championship_data.get('rounds'):
            round_numbers = [int(r) for r in championship_data['rounds'].split(',')]
            round_points_data = get_round_points_for_championship(drivers, round_numbers)
            championship_data['round_points_data'] = round_points_data
            
    return championship_data

# Function to query all data from the SQLite database
def get_all_data(page=1, per_page=100):
    db = get_db()
    table_name = 'championship_results'

    # Get total count for pagination metadata
    total_count = db.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

    # Calculate offset
    offset = (page - 1) * per_page

    # Fetch paginated data from the table
    rows = db.execute(f"SELECT * FROM {table_name} LIMIT ? OFFSET ?", (per_page, offset)).fetchall()

    # Format data using the helper function
    data = [format_championship_data(row) for row in rows]
    
    return data, total_count

# Flask route to return all data as JSON
@bp.route('/data', methods=['GET'])
def get_data_route():
    """
    Fetch All Championship Data
    This endpoint retrieves all championship results stored in the database.
    ---
    parameters:
      - name: page
        in: query
        type: integer
        default: 1
        description: The page number to retrieve.
      - name: per_page
        in: query
        type: integer
        default: 100
        description: The number of results to retrieve per page.
    responses:
      200:
        description: A paginated list of all championship results.
    """
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)
    
    data, total_count = get_all_data(page, per_page)
    
    total_pages = (total_count + per_page - 1) // per_page
    
    response = {
        "total_results": total_count,
        "total_pages": total_pages,
        "current_page": page,
        "per_page": per_page,
        "next_page": f"/api/data?page={page + 1}&per_page={per_page}" if page < total_pages else None,
        "prev_page": f"/api/data?page={page - 1}&per_page={per_page}" if page > 1 else None,
        "results": data
    }
    
    return jsonify(response)

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

    championship_data = format_championship_data(row, with_round_points=True)

    if championship_data:
        return jsonify(championship_data)
    else:
        return jsonify({"error": "Championship not found"}), 404
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


@bp.route('/all_championship_wins', methods=['GET'])
def all_championship_wins_route():
    """
    API route wrapper for all_championship_wins to expose it at `/api/all_championship_wins`.
    """
    return all_championship_wins()






# Cache for expensive queries
_highest_position_cache = None

@bp.route('/highest_position', methods=['GET'])
def highest_position():
    """
    Get the Highest Championship Position for Each Driver
    This endpoint returns the best final championship ranking for every driver, including up to the 5 largest championship IDs where this rank was achieved.

    ULTRA-OPTIMIZED: Uses smart heuristics and caching.
    Key insight: Best positions occur in championships with MORE races.
    ---
    parameters:
      - name: refresh
        in: query
        type: boolean
        required: false
        description: Set to true to bypass cache and recalculate
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are objects containing their highest rank and a list of up to 5 corresponding championship IDs.
    """
    global _highest_position_cache

    # Check if we should bypass cache
    refresh = request.args.get('refresh', 'false').lower() == 'true'

    # Return cached result if available and not refreshing
    if _highest_position_cache is not None and not refresh:
        return jsonify(_highest_position_cache)

    db = get_db()

    # ULTRA-OPTIMIZED APPROACH:
    # Key insight: The best position for each driver occurs in championships with MORE races
    # Strategy: Start from max races and work backwards until all drivers found their best position

    # Step 1: Get the max number of races
    max_races_row = db.execute("SELECT MAX(num_races) as max_races FROM championship_results").fetchone()
    max_races = max_races_row['max_races']

    # Step 2: Get all drivers from any championship
    sample_row = db.execute("SELECT standings FROM championship_results LIMIT 1").fetchone()
    if not sample_row:
        return jsonify([])

    all_drivers = [driver.strip() for driver in sample_row['standings'].split(",")]
    drivers_to_find = set(all_drivers)
    highest_positions = {}

    # Step 3: Process championships starting from max races down
    # Most drivers will find their best position in championships with many races
    for num_races in range(max_races, 0, -1):
        if not drivers_to_find:
            break  # All drivers found

        # Get championships with this number of races (limited sample for performance)
        query = """
        SELECT championship_id, standings
        FROM championship_results
        WHERE num_races = ?
        ORDER BY championship_id DESC
        LIMIT 10000
        """
        rows = db.execute(query, (num_races,)).fetchall()

        for row in rows:
            championship_id = row['championship_id']
            standings = row['standings']
            drivers_list = [d.strip() for d in standings.split(",")]

            for position, driver in enumerate(drivers_list, start=1):
                # First time seeing this driver
                if driver not in highest_positions:
                    highest_positions[driver] = {
                        "position": position,
                        "championship_ids": [championship_id]
                    }
                    # If this is position 1, we've found the best possible
                    if position == 1:
                        drivers_to_find.discard(driver)
                # Found a BETTER position for this driver
                elif position < highest_positions[driver]["position"]:
                    highest_positions[driver] = {
                        "position": position,
                        "championship_ids": [championship_id]
                    }
                    # If this is position 1, we've found the best possible
                    if position == 1:
                        drivers_to_find.discard(driver)
                # Same position, add more championship IDs
                elif position == highest_positions[driver]["position"]:
                    if len(highest_positions[driver]["championship_ids"]) < 5:
                        highest_positions[driver]["championship_ids"].append(championship_id)

    # Step 4: For any remaining drivers (edge case), do a targeted search
    if drivers_to_find:
        for driver in list(drivers_to_find):
            query = """
            SELECT championship_id, standings
            FROM championship_results
            WHERE standings LIKE ?
            ORDER BY num_races DESC, championship_id DESC
            LIMIT 1000
            """
            pattern = f"%{driver}%"
            rows = db.execute(query, (pattern,)).fetchall()

            for row in rows:
                championship_id = row['championship_id']
                standings = row['standings']
                drivers_list = [d.strip() for d in standings.split(",")]

                try:
                    position = drivers_list.index(driver) + 1

                    if driver not in highest_positions:
                        highest_positions[driver] = {
                            "position": position,
                            "championship_ids": [championship_id]
                        }
                    elif position < highest_positions[driver]["position"]:
                        highest_positions[driver] = {
                            "position": position,
                            "championship_ids": [championship_id]
                        }
                    elif position == highest_positions[driver]["position"]:
                        if len(highest_positions[driver]["championship_ids"]) < 5:
                            highest_positions[driver]["championship_ids"].append(championship_id)
                except ValueError:
                    continue

    # Sort the results by position
    sorted_positions = sorted(highest_positions.items(), key=lambda item: item[1]['position'])

    # Create a list of dictionaries to preserve order
    ordered_highest_positions = [
        {'driver': k, 'position': v['position'], 'championship_ids': v['championship_ids']}
        for k, v in sorted_positions
    ]

    # Cache the result
    _highest_position_cache = ordered_highest_positions

    return jsonify(ordered_highest_positions)


@bp.route('/clear-cache', methods=['POST'])
def clear_cache():
    """
    Clear all API caches
    Useful after reprocessing data to ensure fresh results.
    ---
    responses:
      200:
        description: Cache cleared successfully
    """
    global _highest_position_cache
    _highest_position_cache = None
    return jsonify({"message": "Cache cleared successfully"})


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
    d1_upper = driver1.upper()
    d2_upper = driver2.upper()

    if d1_upper == d2_upper:
        return jsonify({"error": "Provide two different driver abbreviations"}), 400

    if d1_upper not in DRIVER_NAMES or d2_upper not in DRIVER_NAMES:
        return jsonify({"error": "Invalid driver abbreviation"}), 400

    # This query is complex. It adds commas to the start and end of the standings string
    # to safely find the position of a driver's abbreviation.
    query = f"""
        SELECT
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',') < INSTR(',' || standings || ',', ',' || ? || ',') THEN 1 ELSE 0 END) as driver1_wins,
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',') > INSTR(',' || standings || ',', ',' || ? || ',') THEN 1 ELSE 0 END) as driver2_wins
        FROM championship_results
        WHERE INSTR(standings, ?) > 0 AND INSTR(standings, ?) > 0;
    """
    result = db.execute(query, (d1_upper, d2_upper, d1_upper, d2_upper, d1_upper, d2_upper)).fetchone()
    
    return jsonify({
        d1_upper: result['driver1_wins'],
        d2_upper: result['driver2_wins']
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

@bp.route('/driver_positions', methods=['GET'])
def driver_positions():
    """
    Count Driver Finishes in a Specific Position
    Counts how many times each driver finished in a given position.
    ---
    parameters:
      - name: position
        in: query
        type: integer
        required: true
        description: The championship position to count.
    responses:
      200:
        description: A JSON object with drivers and their count of finishes in the specified position.
    """
    position = request.args.get('position', type=int)
    if position is None or position < 1:
        return jsonify({"error": "A valid 'position' parameter is required."}), 400

    db = get_db()

    # This query extracts the driver from the specified position in the comma-separated standings string.
    # The logic to extract the Nth element is complex in SQL.
    # We will fetch all standings and process them in Python.
    query = "SELECT standings FROM championship_results"
    rows = db.execute(query).fetchall()

    total_championships = len(rows)
    position_counts = {}
    for row in rows:
        standings = row['standings'].split(',')
        if len(standings) >= position:
            driver = standings[position - 1].strip()
            if driver:
                position_counts[driver] = position_counts.get(driver, 0) + 1
    
    # Sort by count descending
    sorted_counts = sorted(position_counts.items(), key=lambda item: item[1], reverse=True)

    # Format the data with percentages
    result_data = []
    for driver, count in sorted_counts:
        percentage = (count / total_championships) * 100 if total_championships > 0 else 0
        result_data.append({
            "driver": driver,
            "count": count,
            "percentage": round(percentage, 2)
        })
    
    return jsonify(result_data)

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

    drivers = sorted(driver_total_wins.keys())

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

    # Sort driver_data based on the percentage in the last season length column
    if driver_data and season_lengths:
        driver_data.sort(key=lambda x: x['percentages'][-1] if x['percentages'] else 0, reverse=True)

    response_data = {
        "season_lengths": season_lengths,
        "possible_seasons": [seasons_per_length.get(l, 0) for l in season_lengths],
        "drivers_data": driver_data,
        "driver_names": DRIVER_NAMES
    }

    return jsonify(response_data)

@bp.route('/create_championship', methods=['GET'])
def create_championship():
    """
    Finds an existing championship from a list of rounds and returns its URL.
    """
    rounds_str = request.args.get('rounds')
    if not rounds_str:
        return jsonify({"error": "No rounds provided"}), 400

    try:
        # Sort the round numbers to match the database format
        round_numbers = sorted([int(r) for r in rounds_str.split(',')])
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid round numbers"}), 400

    if not round_numbers:
        return jsonify({"error": "No rounds provided"}), 400

    sorted_rounds_str = ','.join(map(str, round_numbers))

    db = get_db()
    row = db.execute(
        "SELECT championship_id FROM championship_results WHERE rounds = ?",
        (sorted_rounds_str,),
    ).fetchone()

    if row:
        championship_id = row['championship_id']
        return jsonify({'url': url_for('views.championship_page', id=championship_id)})
    else:
        # In a real scenario, you might want a more user-friendly error page.
        return jsonify({"error": "Championship with this combination of rounds not found"}), 404
