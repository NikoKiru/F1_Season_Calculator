import pandas as pd
import itertools
import sqlite3
import numpy as np

# Step 1: Read the CSV file and convert to NumPy for performance
def read_csv(file_path):
    data = pd.read_csv(file_path)
    drivers = data.iloc[:, 0].to_numpy()  # Driver names as NumPy array
    scores = data.iloc[:, 1:].to_numpy()  # Scores as NumPy array
    return drivers, scores

# Step 2: Generate subsets of races
def generate_race_combinations(num_races):
    for r in range(1, num_races + 1):
        for combination in itertools.combinations(range(num_races), r): # Use 0-based index
            yield combination

# Step 3: Calculate championship standings using NumPy
def calculate_standings(drivers, scores, race_subset):
    # Sum scores for the given subset of races. This is much faster in NumPy.
    subset_scores = scores[:, race_subset].sum(axis=1)
    
    # Sort drivers based on scores
    sorted_indices = np.argsort(-subset_scores) # Sort in descending order
    sorted_drivers = drivers[sorted_indices]
    
    return sorted_drivers

# Step 4: Save to SQLite database
def save_to_database(db_name, table_name, championship_data):
    if not championship_data:
        return
        
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
    
    # Insert data in bulk
    cursor.executemany(f"""
    INSERT INTO {table_name} (num_races, rounds, standings)
    VALUES (?, ?, ?);
    """, championship_data)
    
    conn.commit()
    conn.close()

# Main function
def main(csv_path, db_name, table_name, batch_size=100000):
    # Step 1: Read input CSV into NumPy arrays
    drivers, scores = read_csv(csv_path)
    num_races = scores.shape[1]

    # Step 2: Get a generator for race combinations
    race_combinations_generator = generate_race_combinations(num_races)

    championship_data_batch = []
    
    # Step 3: Process each combination
    for i, race_subset in enumerate(race_combinations_generator):
        # Calculate standings using the optimized NumPy function
        sorted_drivers = calculate_standings(drivers, scores, race_subset)
        
        # Prepare data for database
        standings_str = ','.join(sorted_drivers)
        # Add 1 to race indices for rounds string to be 1-based
        rounds_str = ','.join(map(str, [r + 1 for r in race_subset]))
        championship_data_batch.append((len(race_subset), rounds_str, standings_str))
        
        # Step 4: Save to database in batches
        if (i + 1) % batch_size == 0:
            save_to_database(db_name, table_name, championship_data_batch)
            print(f"Processed and saved {i + 1} combinations...")
            championship_data_batch = []
    
    # Save any remaining data
    if championship_data_batch:
        save_to_database(db_name, table_name, championship_data_batch)
        print(f"Processed and saved final batch of {len(championship_data_batch)} combinations.")

    print(f"All data saved to {db_name}, table: {table_name}")

# Run the script
if __name__ == "__main__":
    csv_path = "championships.csv"
    db_name = "championships.db"
    table_name = "championship_results"
    main(csv_path, db_name, table_name)
