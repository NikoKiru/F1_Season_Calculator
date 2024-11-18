import pandas as pd
import itertools
import sqlite3

# Step 1: Read the CSV file
def read_csv(file_path):
    data = pd.read_csv(file_path)
    drivers = data.iloc[:, 0]  # Driver names
    scores = data.iloc[:, 1:]  # Scores
    return drivers, scores

# Step 2: Generate subsets of races
def generate_race_combinations(num_races):
    all_combinations = []
    for r in range(1, num_races + 1):
        combinations = list(itertools.combinations(range(1, num_races + 1), r))
        all_combinations.extend(combinations)
    return all_combinations

# Step 3: Calculate championship standings
def calculate_standings(drivers, scores, race_subset):
    subset_scores = scores.iloc[:, [race - 1 for race in race_subset]].sum(axis=1)
    standings = pd.DataFrame({
        'Driver': drivers,
        'Score': subset_scores
    }).sort_values(by='Score', ascending=False).reset_index(drop=True)
    return standings

# Step 4: Save to SQLite database
def save_to_database(db_name, table_name, championship_data):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    
    # Create table if not exists
    cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
        num_races INTEGER,
        rounds TEXT,
        standings TEXT
    );
    """)
    conn.commit()
    
    # Insert data
    for data in championship_data:
        cursor.execute(f"""
        INSERT INTO {table_name} (num_races, rounds, standings)
        VALUES (?, ?, ?);
        """, data)
    conn.commit()
    conn.close()

# Main function
def main(csv_path, db_name, table_name):
    # Step 1: Read input CSV
    drivers, scores = read_csv(csv_path)
    num_races = scores.shape[1]

    # Step 2: Generate combinations of races
    race_combinations = generate_race_combinations(num_races)

    championship_data = []
    
    # Step 3: Process each combination
    for race_subset in race_combinations:
        standings = calculate_standings(drivers, scores, race_subset)
        
        # Prepare data for database
        standings_str = ', '.join(standings['Driver'].tolist())
        championship_data.append((len(race_subset), ','.join(map(str, race_subset)), standings_str))
    
    # Step 4: Save to database
    save_to_database(db_name, table_name, championship_data)
    print(f"Data saved to {db_name}, table: {table_name}")

# Run the script
if __name__ == "__main__":
    csv_path = "championships.csv."  # Replace with your CSV file path
    db_name = "championships.db"
    table_name = "championship_results"
    main(csv_path, db_name, table_name)
