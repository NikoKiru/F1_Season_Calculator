from flask import Flask, jsonify, request, render_template
import sqlite3
from flasgger import Swagger

app = Flask(__name__)
swagger = Swagger(app)

@app.route('/')
def index():
    return render_template('index.html')

# Function to query all data from the SQLite database
def get_all_data():
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    # Replace `table_name` with the actual name of your table
    table_name = 'championship_results'

    # Fetch all data from the table
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()

    # Get column names
    column_names = [description[0] for description in cursor.description]

    # Format data as a list of dictionaries
    data = [dict(zip(column_names, row)) for row in rows]
    print(data)
    conn.close()
    return data

# Flask route to return all data as JSON
@app.route('/api/data', methods=['GET'])
def get_data():
    """
    Fetch All Championship Data
    This endpoint retrieves all championship results stored in the database.
    ---
    responses:
      200:
        description: A list of all championship results.
        schema:
          type: array
          items:
            type: object
            properties:
              championship_id:
                type: integer
              num_races:
                type: integer
              rounds:
                type: string
              standings:
                type: string
              winner:
                type: string
    """
    data = get_all_data()
    return jsonify(data)

@app.route('/api/championship/<int:id>', methods=['GET'])
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
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM championship_results WHERE championship_id = ?", (id,))
    row = cursor.fetchone()
    column_names = [description[0] for description in cursor.description]
    conn.close()

    if row:
        return jsonify(dict(zip(column_names, row)))
    else:
        return jsonify({"error": "Championship not found"}), 404

@app.route('/api/driver_wins/<string:abbreviation>', methods=['GET'])
def count_driver_wins(abbreviation):
    """
    Count Championships Won by a Driver
    This endpoint returns the total number of championships won by a specific driver.
    ---
    parameters:
      - name: abbreviation
        in: path
        type: string
        required: true
        description: The abbreviation of the driver (e.g., VER, HAM).
    responses:
      200:
        description: The total number of wins for the specified driver.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()
    
    table_name = 'championship_results'

    # Query using the indexed 'winner' column
    query = f"SELECT COUNT(*) FROM {table_name} WHERE winner = ?"
    
    cursor.execute(query, (abbreviation.upper(),))
    wins = cursor.fetchone()[0]
    
    conn.close()

    return jsonify({
        "driver": abbreviation.upper(),
        "championships_won": wins
    })

@app.route('/api/all_championship_wins', methods=['GET'])
def all_championship_wins():
    """
    Get All Championship Wins for All Drivers
    This endpoint returns a summary of championship wins for every driver.
    ---
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are their total wins.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'

    # Query to group by the indexed 'winner' column
    query = f"""
        SELECT winner, COUNT(*) as wins
        FROM {table_name}
        GROUP BY winner
        ORDER BY wins DESC
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Format as a dictionary
    championship_wins = {row[0]: row[1] for row in rows}

    return jsonify(championship_wins)

@app.route('/api/highest_rounds_won', methods=['GET'])
def highest_rounds_won():
    """
    Get the Highest Number of Rounds in a Winning Championship for Each Driver
    This endpoint returns the maximum number of races in a championship that each driver has won.
    ---
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are the highest number of rounds in a championship they've won.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    number_of_rounds_column = 'num_races'

    # Query to group by the indexed 'winner' column
    query = f"""
        SELECT winner, MAX({number_of_rounds_column}) as max_rounds
        FROM {table_name}
        GROUP BY winner
    """
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    # Format as a dictionary
    highest_rounds = {row[0]: row[1] for row in rows}

    return jsonify(highest_rounds)

@app.route('/api/largest_championship_wins', methods=['GET'])
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

    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    championship_id_column = 'championship_id'

    # Query using the indexed 'winner' and 'num_races' columns
    query = f"""
        SELECT {championship_id_column}
        FROM {table_name}
        WHERE num_races = ? AND winner = ?
    """
    cursor.execute(query, (num_races, driver.upper()))
    rows = cursor.fetchall()
    conn.close()

    # Extract championship IDs
    matching_championships = [row[0] for row in rows]

    # Return the matching championship IDs
    return jsonify({driver: matching_championships})

@app.route('/api/highest_position', methods=['GET'])
def highest_position():
    """
    Get the Highest Championship Position for Each Driver
    This endpoint returns the best final championship ranking for every driver, including up to the 5 largest championship IDs where this rank was achieved.
    ---
    responses:
      200:
        description: A JSON object where keys are driver abbreviations and values are objects containing their highest rank and a list of up to 5 corresponding championship IDs.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    standings_column = 'standings'
    championship_id_column = 'championship_id'

    # Query to fetch all standings, ordered by championship_id descending to process largest IDs first
    query = f"SELECT {championship_id_column}, {standings_column} FROM {table_name} ORDER BY {championship_id_column} DESC"
    cursor.execute(query)
    rows = cursor.fetchall()

    conn.close()

    highest_positions = {}

    for row in rows:
        championship_id = row[0]
        standings = row[1]
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


@app.route('/api/head_to_head/<string:driver1>/<string:driver2>', methods=['GET'])
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
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

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
    cursor.execute(query, (d1, d2, d1, d2, d1, d2))
    
    result = cursor.fetchone()
    conn.close()

    return jsonify({
        d1: result[0],
        d2: result[1]
    })

@app.route('/api/min_races_to_win/<string:driver>', methods=['GET'])
def min_races_to_win(driver):
    """
    Minimum Races Needed for a Driver to Win a Championship
    Calculates the smallest number of races a driver needed to win a championship.
    ---
    parameters:
      - name: driver
        in: path
        type: string
        required: true
        description: The driver's abbreviation.
    responses:
      200:
        description: The minimum number of races for a championship win.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    query = "SELECT MIN(num_races) FROM championship_results WHERE winner = ?"
    cursor.execute(query, (driver.upper(),))
    result = cursor.fetchone()
    conn.close()

    return jsonify({
        "driver": driver.upper(),
        "min_races_for_win": result[0] if result else None
    })

@app.route('/api/most_common_runner_up', methods=['GET'])
def most_common_runner_up():
    """
    Most Common Championship Runner-Up
    Counts how many times each driver finished in second place across all scenarios.
    ---
    responses:
      200:
        description: A JSON object with drivers and their count of second-place finishes.
    """
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

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
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()

    runner_up_counts = {row[0]: row[1] for row in rows if row[0]}

    return jsonify(runner_up_counts)


@app.route('/championship/<int:id>')
def championship_page(id):
    data = get_championship(id).get_json()
    if "error" in data:
        return render_template('championship.html', data=None), 404
    return render_template('championship.html', data=data)

@app.route('/all_championship_wins')
def all_championship_wins_page():
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()
    table_name = 'championship_results'
    query = f"""
        SELECT winner, COUNT(*) as wins
        FROM {table_name}
        GROUP BY winner
        ORDER BY wins DESC
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    championship_wins = {row[0]: row[1] for row in rows}
    return render_template('all_championship_wins.html', data=championship_wins)

@app.route('/driver_wins')
def driver_wins_page():
    return render_template('driver_wins.html')

@app.route('/highest_rounds_won')
def highest_rounds_won_page():
    data = highest_rounds_won().get_json()
    return render_template('highest_rounds_won.html', data=data)

@app.route('/highest_position')
def highest_position_page():
    data = highest_position().get_json()
    return render_template('highest_position.html', data=data)

@app.route('/most_common_runner_up')
def most_common_runner_up_page():
    data = most_common_runner_up().get_json()
    return render_template('most_common_runner_up.html', data=data)

@app.route('/head_to_head')
def head_to_head_page():
    return render_template('head_to_head.html')

@app.route('/min_races_to_win')
def min_races_to_win_page():
    return render_template('min_races_to_win.html')

@app.route('/largest_championship_wins')
def largest_championship_wins_page():
    return render_template('largest_championship_wins.html')

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
