from flask import Flask, jsonify, request
import sqlite3

app = Flask(__name__)

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
    data = get_all_data()
    return jsonify(data)

@app.route('/api/championship/<int:id>', methods=['GET'])
def get_championship(id):
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
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()
    
    table_name = 'championship_results'
    standings_column = 'standings'

    # Query to count championships where the driver is the winner
    query = f"""
        SELECT COUNT(*)
        FROM {table_name}
        WHERE SUBSTR({standings_column}, 1, INSTR({standings_column} || ',', ',') - 1) = ?
    """
    
    cursor.execute(query, (abbreviation.upper(),))
    wins = cursor.fetchone()[0]
    
    conn.close()

    return jsonify({
        "driver": abbreviation.upper(),
        "championships_won": wins
    })

@app.route('/api/all_championship_wins', methods=['GET'])
def all_championship_wins():
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    standings_column = 'standings'

    # Query to get the winner of each championship and count the wins
    query = f"""
        SELECT 
            SUBSTR({standings_column}, 1, INSTR({standings_column} || ',', ',') - 1) as winner,
            COUNT(*) as wins
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
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    standings_column = 'standings'
    number_of_rounds_column = 'num_races'

    # Query to get the highest number of rounds for each driver's wins
    query = f"""
        SELECT 
            SUBSTR({standings_column}, 1, INSTR({standings_column} || ',', ',') - 1) as winner,
            MAX({number_of_rounds_column}) as max_rounds
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
    # Get query parameters
    driver = request.args.get('driver')  # Driver abbreviation
    num_races = request.args.get('num_races', type=int)  # Number of races

    if not driver or not num_races:
        return jsonify({"error": "Please provide both 'driver' and 'num_races' as query parameters"}), 400

    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    table_name = 'championship_results'
    standings_column = 'standings'
    number_of_rounds_column = 'num_races'
    championship_id_column = 'championship_id'

    # Query to find championships where the driver won and the number of races matches
    query = f"""
        SELECT {championship_id_column}
        FROM {table_name}
        WHERE {number_of_rounds_column} = ? 
        AND SUBSTR({standings_column}, 1, INSTR({standings_column} || ',', ',') - 1) = ?
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
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    # Replace `table_name` and `standings_column` with actual names
    table_name = 'championship_results'
    standings_column = 'standings'

    # Query to fetch all standings
    query = f"SELECT {standings_column} FROM {table_name}"
    cursor.execute(query)
    rows = cursor.fetchall()

    conn.close()

    # Dictionary to store the highest position for each driver
    highest_positions = {}

    # Process each championship standings
    for row in rows:
        standings = row[0]  # The standings string
        drivers = [driver.strip() for driver in standings.split(",")]  # Split by comma and strip whitespace

        # Update each driver's highest position
        for position, driver in enumerate(drivers, start=1):
            if driver not in highest_positions or position < highest_positions[driver]:
                highest_positions[driver] = position

    # Return the results as JSON
    return jsonify(highest_positions)



# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
