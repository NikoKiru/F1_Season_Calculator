# 🏎️ F1 Season Calculator

[![CI](https://github.com/NikoKiru/F1_Season_Calculator/actions/workflows/ci.yml/badge.svg)](https://github.com/NikoKiru/F1_Season_Calculator/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-3.1.2-black.svg?logo=flask)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub last commit](https://img.shields.io/github/last-commit/NikoKiru/F1_Season_Calculator)](https://github.com/NikoKiru/F1_Season_Calculator/commits/main)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)

> A powerful Python-based tool to analyze Formula 1 championship scenarios. Calculate standings for every possible combination of races and discover fascinating "what-if" scenarios!

![F1 Season Calculator](https://via.placeholder.com/800x400/d10000/ffffff?text=F1+Season+Calculator)

## ✨ Features

- 🏁 **Comprehensive Analysis** - Analyzes all possible race combinations (16.7M+ championships from 24 races)
- ⚡ **Lightning Fast** - Sub-second response times with intelligent caching (>10,000x optimization)
- 🌐 **RESTful API** - Full-featured API with interactive Swagger documentation
- 📱 **Responsive UI** - Modern, mobile-first design with dark mode support
- 📊 **Rich Visualizations** - Driver standings, head-to-head comparisons, probability charts
- 👤 **Individual Driver Profiles** - Detailed stats, charts, and head-to-head records for each driver
- 🎯 **Smart Queries** - Find minimum races needed to win, highest positions, win probabilities
- 🔧 **Easy Setup** - One-command installation with automated configuration
- 🚀 **Production Ready** - Optimized SQLite with WAL mode, indexes, and memory-mapped I/O

## 🎯 Quick Start

Get up and running in under 5 minutes!

```powershell
# 1. Clone the repository
git clone https://github.com/NikoKiru/F1_Season_Calculator.git
cd F1_Season_Calculator

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows PowerShell
# or: source .venv/bin/activate  # Linux/Mac

# 3. Install dependencies
pip install -e .

# 4. Run setup (creates folders, database, sample data)
flask setup

# 5. Add your championship data
# Edit data/championships.csv with your F1 season data

# 6. Process data
flask process-data

# 7. Pre-compute statistics (for instant page loads)
flask compute-stats

# 8. Launch the application
flask run
```

🎉 **That's it!** Visit [http://127.0.0.1:5000](http://127.0.0.1:5000)

## 📖 Table of Contents

- [Installation](#-installation)
- [Usage](#-usage)
- [API Documentation](#-api-documentation)
- [Data Format](#-data-format)
- [Architecture](#-architecture)
- [Performance](#-performance)
- [Contributing](#-contributing)
- [License](#-license)
- [Acknowledgments](#-acknowledgments)

## 💻 Installation

### Prerequisites

- Python 3.10 or higher (tested on 3.10, 3.11, 3.12)
- pip (Python package manager)
- Git

### Detailed Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/NikoKiru/F1_Season_Calculator.git
   cd F1_Season_Calculator
   ```
2. **Set up virtual environment** (recommended)

   ```powershell
   # Windows PowerShell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

   ```bash
   # Linux/Mac
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. **Install the package in development mode**

   ```bash
   pip install -e .
   ```

   This installs:

   - Flask (web framework)
   - Pandas (data processing)
   - NumPy (high-performance arrays)
   - Flasgger (Swagger/OpenAPI docs)
   - python-dotenv (environment variables)
4. **Run the setup wizard**

   ```bash
   flask setup
   ```

   This automatically:

   - ✅ Creates `data/` folder for CSV files
   - ✅ Creates `instance/` folder for database
   - ✅ Initializes SQLite database with optimizations
   - ✅ Creates sample CSV template
   - ✅ Displays next steps

## 🚀 Usage

### Adding Race Data During a Season

The easiest way to track a live season is to add results after each race:

```bash
# After Race 1 (Australia)
flask add-race --season 2026 --race 1 --results "VER:25,NOR:18,LEC:15,PIA:12,HAM:10,RUS:8"

# After Race 2 (China)
flask add-race --season 2026 --race 2 --results "NOR:25,VER:18,LEC:15,HAM:12,PIA:10,RUS:8"

# Check your progress
flask season-status --season 2026
```

Each `add-race` command automatically reprocesses all championship combinations and recomputes statistics. The app is ready to use immediately after.

> **Tip:** Include all drivers who scored points. Drivers not listed get 0 points for that race. All drivers from the season config (`data/seasons/2026.json`) are included in calculations.

### Importing Multiple Races at Once

If you need to catch up on several races, create a CSV and batch import:

```csv
Driver,1,2,3
VER,25,18,25
NOR,18,25,18
LEC,15,15,15
```

```bash
flask add-races-batch --season 2026 --csv path/to/races.csv
```

### Processing a Complete Season

For a full season dataset (like the completed 2025 season):

```bash
# 1. Place your CSV data file
#    data/championships.csv       (default)
#    data/championships_2025.csv  (season-specific)

# 2. Process all championship combinations
flask process-data --season 2025

# 3. Pre-compute statistics for instant page loads
flask compute-stats --season 2025
```

**Processing Time:**

- 24 races → ~2-5 minutes
- Generates 16,777,215 championships (2^24 - 1)

### Running the Application

```bash
# Production server (recommended) - multi-threaded via Waitress
python app.py

# Development server (for debugging only)
python app.py --debug
# or
flask run
```

Then open your browser to:

- **Web Interface:** [http://127.0.0.1:5000](http://127.0.0.1:5000)
- **API Docs:** [http://127.0.0.1:5000/apidocs](http://127.0.0.1:5000/apidocs)

The app defaults to the 2026 season. Use the season dropdown or add `?season=2025` to any URL to view other seasons.

### Docker Deployment

For containerized deployment, use Docker Compose with a volume-mounted database. This avoids copying the large SQLite database into the image:

```bash
# Build and run (mounts local instance/ and data/ directories)
docker-compose up

# Or build manually
docker build -t f1-calculator .
docker run -p 5000:5000 -v ./instance:/app/instance -v ./data:/app/data f1-calculator
```

> **Note:** Process your data locally first (`flask process-data` and `flask compute-stats`), then mount the resulting `instance/` directory into Docker.

### Available Commands

| Command                               | Description                                              |
| ------------------------------------- | -------------------------------------------------------- |
| `flask setup`                       | First-time setup (creates folders, database, sample CSV) |
| `flask init-db`                     | Initialize or update database schema                     |
| `flask init-db --clear`             | Reset database (deletes all data)                        |
| `flask process-data`                | Process CSV and generate championships                   |
| `flask process-data --season YYYY`  | Process season-specific CSV file                         |
| `flask compute-stats`               | Pre-compute driver statistics for all seasons            |
| `flask compute-stats --season YYYY` | Pre-compute statistics for a specific season             |
| `flask run`                         | Start the development server                             |

#### Season Management Commands

| Command                                                            | Description                                   |
| ------------------------------------------------------------------ | --------------------------------------------- |
| `flask add-race --season YYYY --race N --results "VER:25,NOR:18"`| Add a single race result for a season         |
| `flask add-races-batch --season YYYY --csv path/to/file.csv`    | Import multiple races from a CSV file         |
| `flask season-status`                                            | Show data status for all seasons              |
| `flask season-status --season YYYY`                              | Show data status for a specific season        |
| `flask clear-season --season YYYY --confirm`                     | Delete all data for a season                  |

> **Performance Note**: After processing data, run `flask compute-stats` to pre-compute driver statistics. This makes the Highest Position page load instantly (~20ms vs 50+ seconds).

## 📡 API Documentation

### REST API Endpoints

The application provides a comprehensive REST API with the following endpoints:

| Endpoint                                  | Method | Description                                               |
| ----------------------------------------- | ------ | --------------------------------------------------------- |
| `/api/data`                             | GET    | Paginated championship data                               |
| `/api/championship/<id>`                | GET    | Specific championship details                             |
| `/api/all_championship_wins`            | GET    | Championship wins per driver                              |
| `/api/highest_position`                 | GET    | Best position achieved by each driver with enriched stats |
| `/api/head_to_head/<driver1>/<driver2>` | GET    | Compare two drivers                                       |
| `/api/min_races_to_win`                 | GET    | Minimum races needed to win                               |
| `/api/driver_positions?position=N`      | GET    | How many times each driver finished in position N         |
| `/api/championship_win_probability`     | GET    | Win probability based on number of races                  |
| `/api/driver/<code>/stats`              | GET    | Aggregated statistics for a specific driver               |
| `/api/driver/<code>/position/<n>`       | GET    | All championships where driver finished in position N     |
| `/api/create_championship`              | POST   | Find championship by specific rounds                      |
| `/api/clear_cache`                      | POST   | Clear API caches                                          |

### Interactive Documentation

Visit [http://127.0.0.1:5000/apidocs](http://127.0.0.1:5000/apidocs) when the server is running for:

- 📝 Complete API reference
- 🧪 Try-it-out functionality
- 📊 Request/response examples
- 🔍 Schema definitions

### Example API Usage

```python
import requests

# Get all championship wins
response = requests.get('http://127.0.0.1:5000/api/all_championship_wins')
wins = response.json()
print(f"VER wins: {wins['VER']}")

# Head-to-head comparison
response = requests.get('http://127.0.0.1:5000/api/head_to_head/VER/NOR')
comparison = response.json()
print(f"VER finished ahead: {comparison['driver1_ahead_count']} times")

# Get highest positions (enriched with max races and winning margin)
response = requests.get('http://127.0.0.1:5000/api/highest_position')
positions = response.json()
for driver in positions:
    margin_info = f", margin: +{driver['best_margin']}" if driver['best_margin'] else ""
    print(f"{driver['driver']}: P{driver['position']} ({driver['max_races']} races){margin_info}")
```

## 📊 Data Format

### CSV Structure

The `championships.csv` file should follow this format:

```csv
Driver,1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24
VER,25,18,25,15,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25
NOR,18,25,18,25,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18,25,18
```

### Field Specifications

| Field      | Type    | Description                               | Required |
| ---------- | ------- | ----------------------------------------- | -------- |
| `Driver` | String  | Three-letter driver code (e.g., VER, NOR) | Yes      |
| `1..N`   | Integer | Points scored in each race                | Yes      |

### Season Configuration

Season data (drivers, teams, races) is stored in JSON config files at `data/seasons/{year}.json`:

```json
{
    "season": 2025,
    "teams": {
        "McLaren": {"color": "#F47600"},
        "Red Bull Racing": {"color": "#4781D7"}
    },
    "drivers": {
        "VER": {
            "name": "Max Verstappen",
            "team": "Red Bull Racing",
            "number": 1,
            "flag": "\ud83c\uddf3\ud83c\uddf1"
        }
    },
    "rounds": {
        "1": "AUS",
        "2": "CHN"
    }
}
```

Season configs for 2025 and 2026 are included. To add a new season, create a new JSON file (e.g., `data/seasons/2027.json`) following this format. The app defaults to the most recent season (currently 2026). Use `?season=YYYY` in the URL to view other seasons.

### Database Schema

```sql
-- Main championship results table
CREATE TABLE championship_results (
    championship_id INTEGER PRIMARY KEY AUTOINCREMENT,
    num_races INTEGER NOT NULL,
    rounds TEXT NOT NULL,          -- Comma-separated race numbers
    standings TEXT NOT NULL,       -- Comma-separated driver codes
    winner TEXT,                   -- Winning driver code
    points TEXT NOT NULL           -- Comma-separated point totals
);

-- Normalized position results for fast position queries
CREATE TABLE position_results (
    championship_id INTEGER NOT NULL,
    driver_code TEXT NOT NULL,
    position INTEGER NOT NULL,
    points INTEGER NOT NULL,
    PRIMARY KEY (championship_id, driver_code),
    FOREIGN KEY (championship_id) REFERENCES championship_results(championship_id)
);

-- Indexes for performance
CREATE INDEX idx_winner ON championship_results (winner);
CREATE INDEX idx_num_races ON championship_results (num_races);
CREATE INDEX idx_winner_num_races ON championship_results (winner, num_races);
CREATE INDEX idx_driver_position ON position_results (driver_code, position);
```

## 🏗️ Architecture

```
F1_Season_Calculator/
├── docs/                    # 📚 Documentation
│   ├── setup/              # Setup guides
│   ├── architecture/       # Architecture docs
│   ├── performance/        # Performance docs
│   ├── ui/                 # UI/UX docs
│   └── api/                # API reference
│
├── championship/           # 🏆 Core application
│   ├── api.py             # REST API endpoints
│   ├── commands.py        # CLI commands
│   ├── views.py           # Web routes
│   ├── logic.py           # Business logic
│   ├── models.py          # Data models (loads from JSON config)
│   └── errors.py          # Error handlers
│
├── static/                 # 🎨 Frontend assets
│   ├── js/                # JavaScript
│   └── style.css          # Responsive CSS
│
├── templates/              # 🖼️ HTML templates
│
├── data/                   # 📊 Championship data
│   ├── seasons/           # Season configuration (JSON)
│   │   └── 2025.json      # 2025 season: drivers, teams, races
│   └── championships.csv  # Race results data
│
├── instance/               # 💾 Database
│
├── tests/                  # 🧪 Test suite
│
├── scripts/                # 🔧 Utility scripts
│
└── config/                 # ⚙️ Configuration
```

For detailed architecture information, see [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)

### Technology Stack

| Layer                     | Technology              | Purpose                |
| ------------------------- | ----------------------- | ---------------------- |
| **Backend**         | Flask 3.1.2             | Web framework          |
| **Data Processing** | Pandas, NumPy           | Fast data manipulation |
| **Database**        | SQLite 3                | Embedded database      |
| **API Docs**        | Flasgger                | Swagger/OpenAPI        |
| **Frontend**        | HTML5, CSS3, Vanilla JS | Responsive UI          |
| **Styling**         | Custom CSS              | Modern design system   |

## ⚡ Performance

### Optimizations Implemented

- **Database Level**

  - WAL (Write-Ahead Logging) mode
  - Memory-mapped I/O (256MB)
  - Optimized cache size (50MB)
  - Strategic indexes on frequently queried columns
  - Batch inserts with transactions
- **Application Level**

  - In-memory caching for expensive queries
  - Smart heuristic-based algorithms
  - Early termination strategies
  - Lazy loading of data
- **Frontend Level**

  - Responsive, mobile-first design
  - Debounced API calls
  - Optimistic UI updates
  - Code splitting

### Performance Benchmarks

| Operation                         | Before      | After           | Improvement             |
| --------------------------------- | ----------- | --------------- | ----------------------- |
| `/api/highest_position`         | 50+ seconds | 20ms            | **2,600x faster** |
| `/api/driver/<code>/stats`      | 2+ minutes  | <100ms          | **1,200x faster** |
| `/api/driver/<code>/position/1` | 3+ minutes  | <200ms          | **900x faster**   |
| Pre-computed stats                | N/A         | ~95s (one-time) | Instant queries         |
| Cached requests                   | N/A         | <1ms            | Instant                 |
| Data import (24 races)            | ~10 min     | ~3 min          | 3.3x faster             |
| Database size                     | N/A         | ~6GB            | 16.7M championships     |

**Key optimizations:**

- Pre-computed driver statistics table for instant highest position queries
- Indexed `winner` column for P1 position queries (uses index instead of LIKE)
- Normalized `position_results` table for instant P2-P20 position queries
- Pagination for large result sets (avoids returning millions of rows)
- Thread-safe caching for repeated requests

For detailed performance analysis, see [docs/performance/PERFORMANCE_OPTIMIZATION.md](docs/performance/PERFORMANCE_OPTIMIZATION.md)

## 🎨 UI/UX Features

- ✨ **Modern Design** - Clean, professional interface
- 📱 **Fully Responsive** - Mobile, tablet, desktop optimized
- 🌙 **Dark Mode** - Automatic system theme detection
- 🎯 **Sticky Headers** - Headers follow scroll
- 🔄 **Smooth Animations** - Professional transitions
- 📊 **Interactive Tables** - Sortable, scrollable
- 🎨 **F1-Themed** - Red color scheme matching Formula 1
- ♿ **Accessible** - Semantic HTML, keyboard navigation

For UI documentation, see [docs/ui/UI_IMPROVEMENTS.md](docs/ui/UI_IMPROVEMENTS.md)

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=championship --cov-report=html

# Run specific test file
pytest tests/test_api.py
```

### Test Coverage Goals

- Minimum coverage threshold: 30% (enforced in CI)
- Target coverage: 80%+

## 🚀 CI/CD Pipeline

This project uses GitHub Actions for continuous integration and deployment.

### Workflows

| Workflow                  | Trigger         | Description                                         |
| ------------------------- | --------------- | --------------------------------------------------- |
| **CI**              | Push/PR to main | Lint, security scan, test (Python 3.10-3.12), build |
| **CD - Staging**    | Push to main    | Auto-deploy to staging after CI passes              |
| **CD - Production** | Manual          | Deploy specific version with approval               |
| **Release**         | Manual          | Create semantic version releases with changelog     |

### CI Pipeline

The CI pipeline runs on every push and pull request:

1. **Lint** - Code quality checks with flake8
2. **Security** - Dependency vulnerability scan with pip-audit
3. **Test** - Matrix testing on Python 3.10, 3.11, 3.12 with coverage
4. **App Validation** - Verify Flask app starts correctly
5. **Build** - Create deployment artifact

### Creating a Release

1. Go to **Actions** > **Release**
2. Click **Run workflow**
3. Select version bump type (patch/minor/major)
4. Workflow creates tag, changelog, and GitHub release

### Deploying to Production

1. Go to **Actions** > **CD - Production**
2. Enter the version tag (e.g., `v1.2.3`)
3. Type `deploy` to confirm
4. Requires environment approval (configure in repo settings)

## 🤝 Contributing

Contributions are welcome! Whether it's:

- 🐛 Bug reports
- 💡 Feature requests
- 📝 Documentation improvements
- 🔧 Code contributions

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Inspiration:** [ChainBear](https://www.youtube.com/@ChainBear) for F1 analysis content
- **Community:** F1 data analysis enthusiasts
- **Tools:** Flask, Pandas, NumPy communities
- **Contributors:** Everyone who has contributed to this project

## 📚 Documentation

- **[Quick Start Guide](docs/setup/QUICKSTART.md)** - Get running in 5 minutes
- **[Setup Guide](docs/setup/SETUP_GUIDE.md)** - Comprehensive installation
- **[Architecture](docs/architecture/ARCHITECTURE.md)** - System design
- **[Performance](docs/performance/PERFORMANCE_OPTIMIZATION.md)** - Optimization details
- **[UI/UX](docs/ui/UI_IMPROVEMENTS.md)** - Design system
- **[API Reference](docs/api/API_REFERENCE.md)** - Complete API docs

## 🔗 Links

- **Repository:** [https://github.com/NikoKiru/F1_Season_Calculator](https://github.com/NikoKiru/F1_Season_Calculator)
- **Issues:** [https://github.com/NikoKiru/F1_Season_Calculator/issues](https://github.com/NikoKiru/F1_Season_Calculator/issues)
- **Releases:** [https://github.com/NikoKiru/F1_Season_Calculator/releases](https://github.com/NikoKiru/F1_Season_Calculator/releases)

## 📊 Project Stats

- **Lines of Code:** ~4,000
- **Championships Analyzed:** 16,777,215 (24 races)
- **API Endpoints:** 12
- **Web Pages:** 15
- **Response Time:** <1 second (cached)
- **Database Size:** ~1.5 GB (24 races)

## 🎯 Roadmap

- [ ] Implement real-time F1 API integration
- [ ] Add user accounts and saved analyses
- [ ] Create data visualization dashboard
- [ ] Add export to PDF/Excel
- [ ] Implement GraphQL API
- [ ] Add multi-season comparison
- [ ] Create mobile app

## 💬 Support

- **Questions?** Open a [GitHub Discussion](https://github.com/NikoKiru/F1_Season_Calculator/discussions)
- **Bugs?** Report an [Issue](https://github.com/NikoKiru/F1_Season_Calculator/issues)
- **Ideas?** Submit a [Feature Request](https://github.com/NikoKiru/F1_Season_Calculator/issues/new)

---

<p align="center">
  Made with ❤️ and ☕ for Formula 1 fans
</p>

<p align="center">
  <sub>🏎️ May the fastest driver win! 🏁</sub>
</p>
