# F1 Season Calculator

![Python](https://img.shields.io/badge/python-3.6+-blue.svg)
![Flask](https://img.shields.io/badge/flask-%23000.svg?style=for-the-badge&logo=flask&logoColor=white)
![Pandas](https://img.shields.io/badge/pandas-%23150458.svg?style=for-the-badge&logo=pandas&logoColor=white)
![SQLite](https://img.shields.io/badge/sqlite-%2307405e.svg?style=for-the-badge&logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)
![GitHub last commit](https://img.shields.io/github/last-commit/NikoKiru/F1_Season_Calculator)

A Python-based tool to analyze Formula 1 championship scenarios. It calculates standings for every possible combination of races from a given season's data, providing insights into how the championship could have unfolded. The results are exposed through a Flask-based REST API and a user-friendly web interface.

## Features

- **Data Processing**: Reads F1 race data from a CSV file.
- **Championship Simulation**: Generates all possible subsets of races to simulate different championship scenarios.
- **Standings Calculation**: Calculates the championship standings for each race combination.
- **Database Storage**: Stores all generated championship standings in a SQLite database.
- **REST API**: Exposes the championship data through a Flask API with interactive Swagger documentation.
- **Web Interface**: A user-friendly frontend to visualize and interact with the API endpoints.
- **Scalable Architecture**: Built using the Flask Application Factory pattern for better organization.
- **Custom CLI Commands**: Provides commands for easy database initialization and data processing.

## Project Structure

The project is organized into a scalable Flask application package:

```
F1_Season_Calculator/
├── data/                 # Contains the raw data files (e.g., championships.csv)
├── F1_Season_Calculator/   # The main Flask application package
│   ├── __init__.py       # Application factory
│   ├── api.py            # Contains all REST API endpoints
│   ├── commands.py       # Custom Flask CLI commands (e.g., process-data)
│   ├── db.py             # Database initialization and management
│   ├── static/           # CSS and JavaScript files
│   ├── templates/        # HTML templates for the web interface
│   └── views.py          # Routes for rendering web pages
├── instance/             # Instance-specific data (e.g., the SQLite database)
├── .flaskenv             # Environment variables for Flask
├── README.md             # This file
└── requirements.txt      # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.6+
- Pip for package management

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/NikoKiru/F1_Season_Calculator.git
    cd F1_Season_Calculator
    ```

2.  **Create a virtual environment (recommended):**
    ```powershell
    # For Windows (PowerShell)
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Usage

**Note**: All commands should be run from the root of the project directory (`F1_Season_Calculator`).

1.  **Prepare Your Data**

    Ensure the `championships.csv` file is located in the `data/` directory. The format should be:
    - The first column must be `Driver`.
    - Subsequent columns represent the points for each race.

    **Example `data/championships.csv`:**
    ```csv
    Driver,1,2,3
    VER,25,18,25
    NOR,18,25,18
    LEC,15,15,15
    ```

2.  **Set the Flask Environment Variable:**
    The `.flaskenv` file should handle this automatically. If not, you can set it manually:
    ```powershell
    # For Windows (PowerShell)
    $env:FLASK_APP = "F1_Season_Calculator"
    ```

3.  **Initialize the Database:**
    This command creates the `championships.db` file in the `instance` folder with the correct schema.
    ```bash
    flask init-db
    ```

4.  **Process the Data:**
    This command reads the data from `data/championships.csv` and populates the database.
    ```bash
    flask process-data
    ```

5.  **Run the Application:**
    ```bash
    flask run
    ```
    -   **Web Interface**: Access the application at `http://127.0.0.1:5000`
    -   **API Documentation (Swagger UI)**: Access the API docs at `http://127.0.0.1:5000/apidocs`

## API Endpoints

The API provides several endpoints to query the championship data. All endpoints return data in JSON format.

An interactive Swagger UI is also available at `/apidocs/` when the server is running, which provides detailed documentation for all endpoints.

### Endpoint Summary

| Method | Endpoint                                               | Description                                                              |
|--------|--------------------------------------------------------|--------------------------------------------------------------------------|
| `GET`  | `/api/data`                                            | Returns all championship data from the database.                         |
| `GET`  | `/api/championship/<id>`                               | Returns data for a specific championship by its ID.                      |
| `GET`  | `/api/driver_wins/<abbreviation>`                      | Returns the total number of championships won by a driver.               |
| `GET`  | `/api/all_championship_wins`                           | Returns a summary of championship wins for all drivers.                  |
| `GET`  | `/api/highest_rounds_won`                              | Returns the highest number of rounds in a winning championship for each driver. |
| `GET`  | `/api/largest_championship_wins`                       | Returns championship IDs won by a driver with a specific number of races. |
| `GET`  | `/api/highest_position`                                | Returns the highest championship position achieved by each driver, including the corresponding championship ID(s).       |
| `GET`  | `/api/head_to_head/<driver1>/<driver2>`                | Compares two drivers to see who finished ahead more often.               |
| `GET`  | `/api/min_races_to_win/<driver>`                       | Finds the minimum number of races a driver needed to win a championship. |
| `GET`  | `/api/most_common_runner_up`                           | Counts how many times each driver finished in second place.              |

### Example Requests

-   **Get all championship wins:**
    ```bash
    curl http://127.0.0.1:5000/api/all_championship_wins
    ```

-   **Get wins for a specific driver:**
    ```bash
    curl http://127.0.0.1:5000/api/driver_wins/VER
    ```

-   **Head-to-head comparison:**
    ```bash
    curl http://127.0.0.1:5000/api/head_to_head/VER/NOR
    ```

## Database Schema

The `championships.db` database contains a single table, `championship_results`, with the following schema:

```sql
CREATE TABLE championship_results (
    championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_races INTEGER,
    rounds TEXT,
    standings TEXT,
    winner TEXT
);
```
-   `rounds`: A comma-separated string of the race numbers included in the championship.
-   `standings`: A comma-separated string of driver abbreviations, ordered by their final rank.
-   `winner`: The abbreviation of the driver who won the championship.

Indexes are created on `winner` and `num_races` to improve query performance.

## Contributing

Contributions are welcome! If you have ideas for improvements or find any issues, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

-   Inspiration from the F1 community and data analysis enthusiasts.
-   Thanks to [ChainBear](https://www.youtube.com/@ChainBear) for the inspiration.
