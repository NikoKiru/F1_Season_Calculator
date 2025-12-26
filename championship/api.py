from typing import Any, Dict, List, Optional, Tuple
from flask import (
    Blueprint, jsonify, request, url_for, Response
)
# Import db module - works with both package and standalone setup
try:
    from ..db import get_db
    from .. import cache
except ImportError:
    import db
    get_db = db.get_db
    from __init__ import cache

try:
    from .models import ROUND_NAMES_2025, DRIVER_NAMES, DRIVERS
    from .logic import get_round_points_for_championship
    from .validators import (
        ErrorCode,
        ValidationError,
        NotFoundError,
        validate_pagination,
        validate_driver_code,
        validate_position,
        validate_championship_id,
        validate_rounds,
        validate_boolean,
        build_error_response,
        format_validation_error,
        format_not_found_error,
    )
except ImportError:
    from championship.models import ROUND_NAMES_2025, DRIVER_NAMES, DRIVERS
    from championship.logic import get_round_points_for_championship
    from championship.validators import (
        ErrorCode,
        ValidationError,
        NotFoundError,
        validate_pagination,
        validate_driver_code,
        validate_position,
        validate_championship_id,
        validate_rounds,
        validate_boolean,
        build_error_response,
        format_validation_error,
        format_not_found_error,
    )

# Cache key constants for consistent naming
CACHE_KEY_HIGHEST_POSITION = 'highest_position'
CACHE_KEY_HEAD_TO_HEAD = 'head_to_head_{driver1}_{driver2}'
CACHE_KEY_DRIVER_POSITIONS = 'driver_positions_{position}'
CACHE_KEY_DRIVER_STATS = 'driver_stats_{driver_code}'

bp = Blueprint('api', __name__, url_prefix='/api')


def format_championship_data(
    row: Optional[Any],
    with_round_points: bool = False
) -> Optional[Dict[str, Any]]:
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
def get_all_data(
    page: int = 1,
    per_page: int = 100
) -> Tuple[List[Optional[Dict[str, Any]]], int]:
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
def get_data_route() -> Response:
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
        description: The number of results to retrieve per page (max 1000).
    responses:
      200:
        description: A paginated list of all championship results.
      400:
        description: Invalid pagination parameters.
    """
    try:
        page, per_page = validate_pagination(
            request.args.get('page'),
            request.args.get('per_page')
        )
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

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
def get_championship(id: int) -> Response:
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
    row = db.execute(
        "SELECT * FROM championship_results WHERE championship_id = ?",
        (id,)
    ).fetchone()

    championship_data = format_championship_data(row, with_round_points=True)

    if championship_data:
        return jsonify(championship_data)
    else:
        response, status = build_error_response(
            code=ErrorCode.CHAMPIONSHIP_NOT_FOUND,
            message="Championship not found",
            details={"championship_id": id}
        )
        return jsonify(response), status


def all_championship_wins() -> Response:
    """
    Get All Championship Wins for All Drivers
    This endpoint returns a summary of championship wins for every driver.
    ---
    responses:
      200:
        description: >
          A JSON object where keys are driver abbreviations
          and values are their total wins.
    """
    db = get_db()

    # Query to group by the indexed 'winner' column
    query = """
        SELECT winner, COUNT(*) as wins
        FROM championship_results
        GROUP BY winner
        ORDER BY wins DESC
    """

    rows = db.execute(query).fetchall()

    # Format as a dictionary
    championship_wins = {row['winner']: row['wins'] for row in rows}

    return jsonify(championship_wins)


@bp.route('/all_championship_wins', methods=['GET'])
def all_championship_wins_route() -> Response:
    """
    API route wrapper for all_championship_wins to expose it at `/api/all_championship_wins`.
    """
    return all_championship_wins()


@bp.route('/highest_position', methods=['GET'])
def highest_position() -> Response:
    """
    Get the Highest Championship Position for Each Driver
    Returns pre-computed data including:
    - Best position achieved
    - Maximum season length where this position was achieved
    - Championship ID for longest season with this position
    - Biggest winning margin (points ahead of 2nd place) for winners

    INSTANT: Uses pre-computed driver_statistics table.
    Run 'flask compute-stats' to update statistics after data changes.
    ---
    responses:
      200:
        description: >
          A JSON array of driver statistics including position, max races,
          winning margin (for winners), and championship details.
    """
    db = get_db()

    # Query the pre-computed statistics table (instant!)
    rows = db.execute("""
        SELECT driver_code, highest_position, highest_position_max_races,
               highest_position_championship_id, best_margin, best_margin_championship_id,
               win_count
        FROM driver_statistics
        ORDER BY highest_position ASC, win_count DESC
    """).fetchall()

    # If no pre-computed stats exist, return empty and warn
    if not rows:
        # Check if championship_results has data
        count = db.execute("SELECT COUNT(*) FROM championship_results").fetchone()[0]
        if count > 0:
            # Data exists but stats not computed - return error message
            return jsonify({
                "error": "Statistics not computed. Run 'flask compute-stats' first.",
                "championship_count": count
            }), 503

        return jsonify([])

    # Format response to match expected structure
    result = [
        {
            'driver': row['driver_code'],
            'position': row['highest_position'],
            'max_races': row['highest_position_max_races'],
            'max_races_championship_id': row['highest_position_championship_id'],
            'best_margin': row['best_margin'],
            'best_margin_championship_id': row['best_margin_championship_id'],
        }
        for row in rows
    ]

    return jsonify(result)


@bp.route('/clear_cache', methods=['POST'])
def clear_cache() -> Response:
    """
    Clear all API caches
    Useful after reprocessing data to ensure fresh results.
    ---
    responses:
      200:
        description: Cache cleared successfully
    """
    cache.clear()
    return jsonify({"message": "Cache cleared successfully"})


@bp.route('/head_to_head/<string:driver1>/<string:driver2>', methods=['GET'])
def head_to_head(driver1: str, driver2: str) -> Response:
    """
    Head-to-Head Driver Comparison
    Compares two drivers to see who finished ahead more often across all championship scenarios.
    Cached for performance.
    ---
    parameters:
      - name: driver1
        in: path
        type: string
        required: true
        description: The abbreviation for the first driver (3-letter code).
      - name: driver2
        in: path
        type: string
        required: true
        description: The abbreviation for the second driver (3-letter code).
    responses:
      200:
        description: A JSON object showing the win count for each driver in the head-to-head comparison.
      400:
        description: Invalid driver code or same driver provided twice.
    """
    try:
        d1_upper = validate_driver_code(driver1, DRIVER_NAMES, "driver1")
        d2_upper = validate_driver_code(driver2, DRIVER_NAMES, "driver2")
    except NotFoundError as e:
        response, status = format_not_found_error(e)
        return jsonify(response), status
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

    if d1_upper == d2_upper:
        response, status = build_error_response(
            code=ErrorCode.INVALID_DRIVER_COMPARISON,
            message="Cannot compare a driver with themselves",
            field="driver2"
        )
        return jsonify(response), status

    # Create a cache key (normalize order so VER-NOR == NOR-VER)
    sorted_drivers = sorted([d1_upper, d2_upper])
    cache_key = CACHE_KEY_HEAD_TO_HEAD.format(driver1=sorted_drivers[0], driver2=sorted_drivers[1])

    # Check cache first (thread-safe)
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        # Return in the order requested
        return jsonify({
            d1_upper: cached_data[d1_upper],
            d2_upper: cached_data[d2_upper]
        })

    db = get_db()

    # This query is complex. It adds commas to the start and end of the standings string
    # to safely find the position of a driver's abbreviation.
    query = """
        SELECT
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',')
                < INSTR(',' || standings || ',', ',' || ? || ',')
                THEN 1 ELSE 0 END) as driver1_wins,
            SUM(CASE WHEN INSTR(',' || standings || ',', ',' || ? || ',')
                > INSTR(',' || standings || ',', ',' || ? || ',')
                THEN 1 ELSE 0 END) as driver2_wins
        FROM championship_results
        WHERE INSTR(standings, ?) > 0 AND INSTR(standings, ?) > 0;
    """
    result = db.execute(
        query,
        (d1_upper, d2_upper, d1_upper, d2_upper, d1_upper, d2_upper)
    ).fetchone()

    response_data = {
        d1_upper: result['driver1_wins'],
        d2_upper: result['driver2_wins']
    }

    # Cache the result (thread-safe)
    cache.set(cache_key, response_data)

    return jsonify(response_data)


@bp.route('/min_races_to_win', methods=['GET'])
def min_races_to_win() -> Response:
    """
    Minimum Races Needed for a Driver to Win a Championship
    Calculates the smallest number of races a driver needed to win a championship.
    ---
    responses:
      200:
        description: The minimum number of races for a championship win for each driver.
    """
    db = get_db()

    query = """
        SELECT winner, MIN(num_races) as min_races
        FROM championship_results
        WHERE winner IS NOT NULL
        GROUP BY winner
        ORDER BY min_races ASC
    """
    results = db.execute(query).fetchall()

    data = {row['winner']: row['min_races'] for row in results}

    return jsonify(data)


@bp.route('/driver_positions', methods=['GET'])
def driver_positions() -> Response:
    """
    Count Driver Finishes in a Specific Position
    Counts how many times each driver finished in a given position.
    Cached for performance.
    ---
    parameters:
      - name: position
        in: query
        type: integer
        required: true
        description: The championship position to count (1-24).
    responses:
      200:
        description: A JSON object with drivers and their count of finishes in the specified position.
      400:
        description: Invalid position parameter.
    """
    try:
        position = validate_position(request.args.get('position'))
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

    # Check cache first (thread-safe)
    cache_key = CACHE_KEY_DRIVER_POSITIONS.format(position=position)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify(cached_result)

    db = get_db()

    # OPTIMIZATION: Use indexed position_results table for instant queries
    # The position_results table has an index on (driver_code, position) making this query fast
    query = """
        SELECT driver_code, COUNT(*) as count
        FROM position_results
        WHERE position = ?
        GROUP BY driver_code
        ORDER BY count DESC
    """
    rows = db.execute(query, (position,)).fetchall()

    # Calculate total championships from the sum of all counts
    total_championships = sum(row['count'] for row in rows)

    # Format the data with percentages
    result_data = []
    for row in rows:
        count = row['count']
        percentage = (count / total_championships) * 100 if total_championships > 0 else 0
        result_data.append({
            "driver": row['driver_code'],
            "count": count,
            "percentage": round(percentage, 2)
        })

    # Cache the result (thread-safe)
    cache.set(cache_key, result_data)

    return jsonify(result_data)


@bp.route('/championship_win_probability', methods=['GET'])
def championship_win_probability() -> Response:
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

    # Sort driver_data based on percentages from right to left (last column first, then second-to-last, etc.)
    # This creates a tuple of percentages in reverse order for sorting
    if driver_data and season_lengths:
        driver_data.sort(key=lambda x: tuple(reversed(x['percentages'])) if x['percentages'] else tuple(), reverse=True)

    response_data = {
        "season_lengths": season_lengths,
        "possible_seasons": [seasons_per_length.get(length, 0) for length in season_lengths],
        "drivers_data": driver_data,
        "driver_names": DRIVER_NAMES
    }

    return jsonify(response_data)


@bp.route('/driver/<string:driver_code>/stats', methods=['GET'])
def driver_stats(driver_code: str) -> Response:
    """
    Get aggregated statistics for a specific driver.
    Uses pre-computed driver_statistics table for instant performance.
    Head-to-head data is computed lazily via separate endpoint.
    ---
    parameters:
      - name: driver_code
        in: path
        type: string
        required: true
        description: The driver abbreviation (3-letter code, e.g., VER, NOR, HAM)
    responses:
      200:
        description: Aggregated driver statistics
      400:
        description: Invalid driver code format
      404:
        description: Driver not found
    """
    try:
        driver_code = validate_driver_code(driver_code, DRIVER_NAMES)
    except NotFoundError as e:
        response, status = format_not_found_error(e)
        return jsonify(response), status
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

    # Check cache first (thread-safe)
    cache_key = CACHE_KEY_DRIVER_STATS.format(driver_code=driver_code)
    cached_result = cache.get(cache_key)
    if cached_result is not None:
        return jsonify(cached_result)

    db = get_db()

    # Get pre-computed stats from driver_statistics table (INSTANT!)
    stats_row = db.execute("""
        SELECT highest_position, highest_position_max_races,
               highest_position_championship_id, best_margin,
               best_margin_championship_id, win_count
        FROM driver_statistics
        WHERE driver_code = ?
    """, (driver_code,)).fetchone()

    # Get total championships count for percentage
    total_query = "SELECT COUNT(*) as total FROM championship_results"
    total_result = db.execute(total_query).fetchone()
    total_championships = total_result['total'] if total_result else 1

    # Use pre-computed data if available
    if stats_row:
        total_wins = stats_row['win_count']
        highest_position = stats_row['highest_position']
        highest_position_championship = stats_row['highest_position_championship_id']
    else:
        # Fallback to indexed query for wins
        wins_query = "SELECT COUNT(*) as wins FROM championship_results WHERE winner = ?"
        wins_result = db.execute(wins_query, (driver_code,)).fetchone()
        total_wins = wins_result['wins'] if wins_result else 0
        highest_position = 20
        highest_position_championship = None

    win_percentage = round((total_wins / total_championships) * 100, 2) if total_championships > 0 else 0

    # Get minimum races to win (fast - uses indexed winner column)
    min_races_query = "SELECT MIN(num_races) as min_races FROM championship_results WHERE winner = ?"
    min_races_result = db.execute(min_races_query, (driver_code,)).fetchone()
    min_races_to_win = min_races_result['min_races'] if min_races_result and min_races_result['min_races'] else None

    # Get win probability by season length (fast - indexed winner column)
    win_prob_by_length = {}
    query = "SELECT num_races, COUNT(*) as wins FROM championship_results WHERE winner = ? GROUP BY num_races"
    for row in db.execute(query, (driver_code,)).fetchall():
        win_prob_by_length[row['num_races']] = row['wins']

    # Get total seasons per length for percentage calculation
    seasons_per_length = {}
    for row in db.execute("SELECT num_races, COUNT(*) as total FROM championship_results GROUP BY num_races").fetchall():
        seasons_per_length[row['num_races']] = row['total']

    win_prob_percentages = {}
    for length, wins in win_prob_by_length.items():
        total = seasons_per_length.get(length, 1)
        win_prob_percentages[length] = round((wins / total) * 100, 2)

    # Position distribution: Use indexed winner column for P1, estimate others
    # Full position distribution is expensive - only include P1 count (from wins)
    position_counts = {1: total_wins} if total_wins > 0 else {}

    response = {
        "driver_code": driver_code,
        "driver_name": DRIVER_NAMES[driver_code],
        "driver_info": DRIVERS[driver_code],
        "total_wins": total_wins,
        "total_championships": total_championships,
        "win_percentage": win_percentage,
        "highest_position": highest_position,
        "highest_position_championship_id": highest_position_championship,
        "min_races_to_win": min_races_to_win,
        "position_distribution": position_counts,
        "win_probability_by_length": win_prob_percentages,
        "seasons_per_length": seasons_per_length
    }

    # Cache the result (thread-safe)
    cache.set(cache_key, response)

    return jsonify(response)


@bp.route('/driver/<string:driver_code>/position/<int:position>', methods=['GET'])
def driver_position_championships(driver_code: str, position: int) -> Response:
    """
    Get championships where a driver finished in a specific position.
    Uses indexed queries for position 1 (winner column) for instant performance.
    Returns paginated results (default 100 per page).
    ---
    parameters:
      - name: driver_code
        in: path
        type: string
        required: true
        description: The driver abbreviation (3-letter code, e.g., VER, NOR, HAM)
      - name: position
        in: path
        type: integer
        required: true
        description: The championship position to filter by (1-20)
      - name: page
        in: query
        type: integer
        default: 1
        description: Page number for pagination
      - name: per_page
        in: query
        type: integer
        default: 100
        description: Results per page (max 500)
    responses:
      200:
        description: Paginated list of championships where driver finished in position
      400:
        description: Invalid driver code or position
      404:
        description: Driver not found
    """
    try:
        driver_code = validate_driver_code(driver_code, DRIVER_NAMES)
    except NotFoundError as e:
        response, status = format_not_found_error(e)
        return jsonify(response), status
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

    if position < 1 or position > 20:
        response, status = build_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Position must be between 1 and 20",
            field="position"
        )
        return jsonify(response), status

    # Parse pagination parameters
    try:
        page = int(request.args.get('page', 1))
        per_page = min(int(request.args.get('per_page', 100)), 500)  # Max 500
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 100
    except ValueError:
        page, per_page = 1, 100

    db = get_db()
    offset = (page - 1) * per_page

    # OPTIMIZATION: For position 1, use the indexed 'winner' column (instant!)
    if position == 1:
        # Get total count using indexed query
        count_result = db.execute(
            "SELECT COUNT(*) as cnt FROM championship_results WHERE winner = ?",
            (driver_code,)
        ).fetchone()
        total_count = count_result['cnt'] if count_result else 0

        # Get paginated results using indexed query
        query = """
            SELECT championship_id, num_races, rounds, standings, points
            FROM championship_results
            WHERE winner = ?
            ORDER BY num_races DESC, championship_id DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute(query, (driver_code, per_page, offset)).fetchall()

        championships = []
        for row in rows:
            standings = [d.strip() for d in row['standings'].split(',')]
            points_list = [int(p) for p in row['points'].split(',')]
            driver_points = points_list[0] if points_list else 0
            margin = points_list[0] - points_list[1] if len(points_list) >= 2 else None

            championships.append({
                'championship_id': row['championship_id'],
                'num_races': row['num_races'],
                'standings': standings,
                'driver_points': driver_points,
                'margin': margin
            })
    else:
        # OPTIMIZATION: Use indexed position_results table for instant queries
        # Get total count using indexed query
        count_result = db.execute(
            "SELECT COUNT(*) as cnt FROM position_results WHERE driver_code = ? AND position = ?",
            (driver_code, position)
        ).fetchone()
        total_count = count_result['cnt'] if count_result else 0

        # Get paginated results using indexed join
        query = """
            SELECT cr.championship_id, cr.num_races, cr.rounds, cr.standings, cr.points,
                   pr.points as driver_points
            FROM position_results pr
            JOIN championship_results cr ON pr.championship_id = cr.championship_id
            WHERE pr.driver_code = ? AND pr.position = ?
            ORDER BY cr.num_races DESC, cr.championship_id DESC
            LIMIT ? OFFSET ?
        """
        rows = db.execute(query, (driver_code, position, per_page, offset)).fetchall()

        championships = []
        for row in rows:
            standings = [d.strip() for d in row['standings'].split(',')]
            points_list = [int(p) for p in row['points'].split(',')]
            driver_points = row['driver_points']
            # Calculate margin: points of driver at position-1 minus driver's points
            margin = points_list[position - 2] - driver_points if position > 1 and len(points_list) >= position else None

            championships.append({
                'championship_id': row['championship_id'],
                'num_races': row['num_races'],
                'standings': standings,
                'driver_points': driver_points,
                'margin': margin
            })

    total_pages = (total_count + per_page - 1) // per_page if total_count > 0 else 1

    return jsonify({
        'driver_code': driver_code,
        'driver_name': DRIVER_NAMES.get(driver_code, driver_code),
        'position': position,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'total_pages': total_pages,
        'championships': championships
    })


@bp.route('/create_championship', methods=['GET'])
def create_championship() -> Response:
    """
    Finds an existing championship from a list of rounds and returns its URL.
    ---
    parameters:
      - name: rounds
        in: query
        type: string
        required: true
        description: Comma-separated list of round numbers (1-24, no duplicates)
    responses:
      200:
        description: URL to the championship page
      400:
        description: Invalid rounds parameter
      404:
        description: Championship not found
    """
    try:
        round_numbers = validate_rounds(request.args.get('rounds'))
    except ValidationError as e:
        response, status = format_validation_error(e)
        return jsonify(response), status

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
        response, status = build_error_response(
            code=ErrorCode.CHAMPIONSHIP_NOT_FOUND,
            message="Championship with this combination of rounds not found",
            details={"rounds": round_numbers}
        )
        return jsonify(response), status
