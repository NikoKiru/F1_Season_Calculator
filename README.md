# F1 Season Calculator 🏎

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
- **Modular Architecture**: Built using the Flask Application Factory pattern and feature-based blueprints for better organization and scalability.
- **Custom CLI Commands**: Provides commands for easy database initialization and data processing.

## Project Structure

The project is organized into a scalable Flask application with a modular, feature-based structure.

```
F1_Season_Calculator/
├── data/                   # Contains the raw data files (e.g., championships.csv)
├── F1_Season_Calculator/     # The main Flask application package
│   ├── championship/       # Feature module for all championship logic
│   │   ├── __init__.py     # Marks the directory as a Python module
│   │   ├── api.py          # Contains all REST API endpoints
│   │   ├── commands.py     # Custom Flask CLI commands
│   │   ├── logic.py        # Business logic for calculations
│   │   ├── models.py       # Data models (e.g., driver and round names)
│   │   └── views.py        # Routes for rendering web pages
│   ├── static/             # CSS, JavaScript, and image files
│   ├── templates/          # HTML templates, including a base template
│   ├── __init__.py         # Application factory (create_app)
│   └── db.py               # Database initialization and management
├── instance/               # Instance-specific data (e.g., the SQLite database)
├── .flaskenv               # Environment variables for Flask
├── README.md               # This file
└── requirements.txt        # Python dependencies
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
    # Windows PowerShell
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    ```

3.  **Install the dependencies:**
    ```powershell
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
    The `.flaskenv` file should handle this automatically. If not, you can set it manually (PowerShell):
    ```powershell
    $env:FLASK_APP = "F1_Season_Calculator"
    ```

3.  **Initialize the Database:**
    Creates `instance\championships.db`, applies PRAGMAs (WAL, cache tuning), and creates indexes.
    ```powershell
    flask init-db
    ```

4.  **Process the Data (optimized bulk import):**
    Reads `data/championships.csv`, generates all championship combinations, and bulk-inserts in a single transaction for speed.
    ```powershell
    flask process-data
    ```
    - During import, durability is relaxed (`synchronous=OFF`) and restored after commit.
    - You can optionally increase throughput by raising the batch size: `flask process-data --batch-size 200000`.

5.  **Run the Application:**
    ```powershell
    flask run
    ```
    -   **Web Interface**: Access the application at `http://127.0.0.1:5000`
    -   **API Documentation (Swagger UI)**: Access the API docs at `http://127.0.0.1:5000/apidocs`

## API Endpoints

The API provides several endpoints to query the championship data. All endpoints return data in JSON format. An interactive Swagger UI is also available at `/apidocs/` when the server is running.

### Endpoint Summary

| Method | Endpoint                                | Description                                                              |
|--------|-----------------------------------------|--------------------------------------------------------------------------|
| `GET`  | `/api/data`                             | Returns paginated championship data from the database.                   |
| `GET`  | `/api/championship/<id>`                | Returns data for a specific championship by its ID.                      |
| `GET`  | `/api/all_championship_wins`            | Returns a summary of championship wins for all drivers.                  |
| `GET`  | `/api/highest_position`                 | Returns the highest championship position achieved by each driver.       |
| `GET`  | `/api/head_to_head/<driver1>/<driver2>` | Compares two drivers to see who finished ahead more often.               |
| `GET`  | `/api/min_races_to_win`                 | Finds the minimum number of races a driver needed to win a championship. |
| `GET`  | `/api/driver_positions`                 | Counts how many times each driver finished in a specific position.       |
| `GET`  | `/api/championship_win_probability`     | Returns the win probability for each driver based on season length.      |
| `GET`  | `/api/create_championship`              | Finds a championship from a list of rounds and redirects to its page.    |

### Example Requests

-   **Get all championship wins:**
    ```bash
    curl http://127.0.0.1:5000/api/all_championship_wins
    ```

-   **Head-to-head comparison:**
    ```bash
    curl http://127.0.0.1:5000/api/head_to_head/VER/NOR
    ```

-   **Get driver positions for 1st place:**
    ```bash
    curl "http://127.0.0.1:5000/api/driver_positions?position=1"
    ```

## Database Schema

The `championships.db` database contains a single table, `championship_results`, with the following schema:

```sql
CREATE TABLE championship_results (
    championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_races INTEGER NOT NULL,
    rounds TEXT NOT NULL,
    standings TEXT NOT NULL,
    winner TEXT,
    points TEXT NOT NULL
);
```
-   `rounds`: A comma-separated string of the race numbers included in the championship.
-   `standings`: A comma-separated string of driver abbreviations, ordered by their final rank.
-   `winner`: The abbreviation of the driver who won the championship.
-   `points`: A comma-separated string of the total points for each driver, in the same order as `standings`.

Indexes are created on `winner`, `num_races`, `winner,num_races`, `rounds`, and `points` to improve query performance. WAL mode and tuned PRAGMAs are applied during initialization for faster reads and writes.

### Performance Notes
- SQLite is configured in WAL mode (`journal_mode=WAL`) with `synchronous=NORMAL`, in-memory temp store, and a larger cache.
- The data import runs inside a single transaction and commits once, significantly reducing IO.
- Exact round-combination lookups (`/api/create_championship`) are accelerated by an index on `rounds`.
- Heavy endpoints like `/api/driver_positions` may benefit from a future derived table (`standings_positions`) for SQL-native aggregation; current Python aggregation works but can be optimized further.

## Contributing

Contributions are welcome! If you have ideas for improvements or find any issues, please open an issue or submit a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

-   Inspiration from the F1 community and data analysis enthusiasts.
-   Thanks to [ChainBear](https://www.youtube.com/@ChainBear) for the inspiration.
