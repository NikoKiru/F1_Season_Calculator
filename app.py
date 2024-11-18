from flask import Flask, jsonify
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
    
    # Replace `table_name` and `standings_column` with your actual table and column names
    table_name = 'championship_results'
    standings_column = 'standings'

    # Query to fetch all standings
    cursor.execute(f"SELECT {standings_column} FROM {table_name}")
    rows = cursor.fetchall()
    
    conn.close()

    # Count championships won by the driver
    wins = sum(1 for row in rows if row[0].split(',')[0] == abbreviation.upper())

    return jsonify({
        "driver": abbreviation.upper(),
        "championships_won": wins
    })

@app.route('/api/all_championship_wins', methods=['GET'])
def all_championship_wins():
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    # Replace `table_name` and `standings_column` with your actual table and column names
    table_name = 'championship_results'
    standings_column = 'standings'

    # Query to fetch all standings
    cursor.execute(f"SELECT {standings_column} FROM {table_name}")
    rows = cursor.fetchall()

    conn.close()

    # Create a dictionary to store the count of championships for each driver
    championship_wins = {}

    for row in rows:
        # Get the first-place abbreviation from the standings
        winner = row[0].split(',')[0]
        championship_wins[winner] = championship_wins.get(winner, 0) + 1

    return jsonify(championship_wins)

@app.route('/api/highest_rounds_won', methods=['GET'])
def highest_rounds_won():
    conn = sqlite3.connect('championships.db')
    cursor = conn.cursor()

    # Replace `table_name` and column names with your actual table and column names
    table_name = 'championship_results'
    standings_column = 'standings'
    number_of_rounds_column = 'num_races'

    # Query to fetch all championships and their corresponding data
    cursor.execute(f"SELECT {standings_column}, {number_of_rounds_column} FROM {table_name}")
    rows = cursor.fetchall()

    conn.close()

    # Dictionary to store the highest number of rounds won by each driver
    highest_rounds = {}

    for row in rows:
        standings = row[0].split(',')
        winner = standings[0]  # The first driver in the standings is the winner
        number_of_rounds = row[1]  # Number of rounds in this championship

        # Update the highest rounds for this driver if this championship's rounds are greater
        if winner not in highest_rounds or number_of_rounds > highest_rounds[winner]:
            highest_rounds[winner] = number_of_rounds

    return jsonify(highest_rounds)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)