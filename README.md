# Racing Championship Analysis Tool

![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![Pandas](https://img.shields.io/badge/pandas-latest-blue.svg)
![SQLite](https://img.shields.io/badge/sqlite-3-green.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)
![Last Commit](https://img.shields.io/github/last-commit/NikoKiru/F1_Season_Calculator)

A Python tool that analyzes racing championship scenarios by calculating standings across different combinations of races. The tool processes race data from a CSV file and stores the results in a SQLite database.

![Build Status](https://img.shields.io/github/workflow/status/NikoKiru/F1_Season_Calculator/CI)
![GitHub issues](https://img.shields.io/github/issues/NikoKiru/F1_Season_Calculator)
![GitHub stars](https://img.shields.io/github/stars/NikoKiru/F1_Season_Calculator)

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
git clone https://github.com/NikoKiru/F1_Season_Calculator.git
cd F1_Season_Calculator
```

2. Install required packages:
```bash
pip install pandas
```

## Usage

1. Prepare your input CSV file with the following format:
   - First column: Driver names
   - Subsequent columns: Race Points

2. Run the script:
```bash
python f1.py
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
Driver,1,1,1
Verstappen,25,18,25
Norris,18,25,18
Leclerc,15,15,15
```

## Contributing

Feel free to submit issues and enhancement requests!

## License

MIT License

## Author

NikoKiru

## Acknowledgments

- Thanks to anyone whose code was used
- Any inspirations
- ChainBear
