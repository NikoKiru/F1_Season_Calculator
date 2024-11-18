# Racing Championship Analysis Tool

A Python tool that analyzes racing championship scenarios by calculating standings across different combinations of races. The tool processes race data from a CSV file and stores the results in a SQLite database.

## Features

- Reads race data from CSV files
- Generates all possible combinations of races
- Calculates championship standings for each combination
- Stores results in a SQLite database for further analysis

## Prerequisites

- Python 3.x
- Required Python packages:
  - pandas
  - itertools (built-in)
  - sqlite3 (built-in)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/racing-championship-analysis.git
cd racing-championship-analysis
```

2. Install required packages:
```bash
pip install pandas
```

## Usage

1. Prepare your input CSV file with the following format:
   - First column: Driver names
   - Subsequent columns: Race scores

2. Run the script:
```bash
python main.py
```

3. Configure the following variables in the script if needed:
   - `csv_path`: Path to your input CSV file
   - `db_name`: Name of the SQLite database
   - `table_name`: Name of the table in the database

## How It Works

1. **Data Input**: The script reads driver names and race scores from a CSV file.

2. **Race Combinations**: Generates all possible combinations of races using Python's itertools.

3. **Standings Calculation**: For each combination of races:
   - Sums the scores for selected races
   - Ranks drivers based on total points
   - Stores the results

4. **Data Storage**: Saves all results to a SQLite database with:
   - Number of races in the combination
   - Specific rounds included
   - Final standings for that combination

## Database Schema

The SQLite database contains a table with the following structure:
```sql
CREATE TABLE championship_results (
    championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_races INTEGER,
    rounds TEXT,
    standings TEXT
);
```

## Input File Format

Example `championships.csv`:
```csv
Driver,Race1,Race2,Race3
Hamilton,25,18,25
Verstappen,18,25,18
Bottas,15,15,15
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

[Add your chosen license here]

## Author

[Your Name]

## Acknowledgments

- Thanks to anyone whose code was used
- Any inspirations
- etc
