# Racing Championship Analysis Tool
![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![Postman](https://img.shields.io/badge/Postman-FF6C37?style=for-the-badge&logo=postman&logoColor=white)

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
Driver,1,2,3
VER,25,18,25
NOR,18,25,18
LEC,15,15,15
```

# Championship Results API

A Flask-based REST API that provides access to racing championship data stored in SQLite. This API allows you to query championship results, driver statistics, and historical racing data.

## Prerequisites

- Python 3.x
- Flask
- SQLite3

## Installation

1. Clone the repository
2. Install the required dependencies:
```bash
pip install flask
```

3. Ensure you have a SQLite database named `championships.db` with a table `championship_results` containing the following columns:
   - championship_id
   - standings (comma-separated list of driver abbreviations)
   - num_races
   - (any additional columns will be included in the API responses)

## API Endpoints

### Get All Championship Data
```
GET /api/data
```
Returns all championship data from the database.

### Get Specific Championship
```
GET /api/championship/<id>
```
Returns data for a specific championship by ID.

**Parameters:**
- `id` (integer): The championship ID

### Get Driver's Championship Wins
```
GET /api/driver_wins/<abbreviation>
```
Returns the number of championships won by a specific driver.

**Parameters:**
- `abbreviation` (string): Driver's abbreviation code

### Get All Championship Wins
```
GET /api/all_championship_wins
```
Returns a summary of championship wins for all drivers.

### Get Highest Rounds Won
```
GET /api/highest_rounds_won
```
Returns the highest number of rounds won by each driver in a single championship.

## Response Formats

All endpoints return data in JSON format. Here are example responses:

### Single Championship Response
```json
{
    "championship_id": 1,
    "standings": "HAM,VER,BOT",
    "num_races": 22
}
```

### Driver Wins Response
```json
{
    "driver": "HAM",
    "championships_won": 7
}
```

## Error Handling

The API includes basic error handling:
- Returns 404 if a requested championship is not found
- Standard Flask error handling for invalid routes and methods

## Running the Application

To start the server:
```bash
python app.py
```

The API will be available at `http://localhost:5000`

## Development

The application runs in debug mode by default when started directly. For production deployment, make sure to disable debug mode and configure appropriate security measures.

## Database Schema

The application expects a SQLite database with the following structure:

```sql
CREATE TABLE championship_results (
    championship_id INTEGER PRIMARY KEY,
    standings TEXT,
    num_races INTEGER
    -- Additional columns as needed
);
```

## Notes

- The standings column stores driver abbreviations as comma-separated values
- The first driver in the standings is considered the championship winner
- All driver abbreviations are stored and compared in uppercase

## Security Considerations

- The application currently uses string formatting for table names. In a production environment, consider using parameterized queries for all database operations
- Implement appropriate authentication and rate limiting for production use
- Consider adding input validation for driver abbreviations and other parameters

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
