# F1 Season Calculator - Architecture Overview

## 🎯 System Overview

The F1 Season Calculator is a Flask-based web application that analyzes Formula 1 championship scenarios by calculating standings for every possible combination of races from a season's data.

### Key Capabilities

- **16.7 million championships** analyzed from 24-race season
- **Sub-second response times** with intelligent caching
- **RESTful API** with Swagger documentation
- **Responsive web interface** with modern UI/UX
- **SQLite database** with optimized indexes and PRAGMAs

## 🏗️ Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│  ┌──────────────────┐    ┌──────────────────┐                   │
│  │  Web Browser     │    │  API Clients     │                   │
│  │  (HTML/CSS/JS)   │    │  (JSON/REST)     │                   │
│  └────────┬─────────┘    └────────┬─────────┘                   │
└───────────┼──────────────────────┼──────────────────────────────┘
            │                      │
            ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Flask Application                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Application Factory                    │   │
│  │                  (__init__.py:create_app)                │   │
│  └───────────────┬───────────────────────┬──────────────────┘   │
│                  │                       │                      │
│     ┌────────────▼────────┐   ┌─────────▼──────────┐           │
│     │   Blueprint: API    │   │  Blueprint: Views  │           │
│     │  (championship/api) │   │ (championship/views)│           │
│     │                     │   │                    │           │
│     │  • GET /api/data   │   │  • GET /          │           │
│     │  • GET /api/...    │   │  • GET /highest_  │           │
│     │  • Swagger docs    │   │  • GET /head_to_  │           │
│     └──────────┬──────────┘   └─────────┬─────────┘           │
│                │                        │                      │
│     ┌──────────▼────────────────────────▼──────────┐           │
│     │         Business Logic Layer                 │           │
│     │      (championship/logic.py)                 │           │
│     │                                               │           │
│     │  • Championship calculations                 │           │
│     │  • Points aggregation                       │           │
│     │  • Standings generation                     │           │
│     └──────────────────┬──────────────────────────┘           │
│                        │                                       │
│     ┌──────────────────▼──────────────────────────┐           │
│     │           CLI Commands Layer                │           │
│     │       (championship/commands.py)            │           │
│     │                                             │           │
│     │  • flask init-db   (initialize database)   │           │
│     │  • flask setup     (first-time setup)      │           │
│     │  • flask process-data (generate combos)    │           │
│     └──────────────────┬──────────────────────────┘           │
└────────────────────────┼────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Data Layer (db.py)                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Database Connection Pool                     │   │
│  │           • SQLite with WAL mode                         │   │
│  │           • Memory-mapped I/O (256MB)                    │   │
│  │           • Optimized cache (50MB)                       │   │
│  └───────────────┬──────────────────────────────────────────┘   │
└──────────────────┼──────────────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                 SQLite Database (instance/)                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │          championship_results Table                       │   │
│  │  ┌───────────────────────────────────────────────────┐   │   │
│  │  │  • championship_id (PRIMARY KEY)                  │   │   │
│  │  │  • num_races (INTEGER, INDEXED)                   │   │   │
│  │  │  • rounds (TEXT, INDEXED)                         │   │   │
│  │  │  • standings (TEXT)                               │   │   │
│  │  │  • winner (TEXT, INDEXED)                         │   │   │
│  │  │  • points (TEXT, INDEXED)                         │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │          position_results Table                           │   │
│  │  ┌───────────────────────────────────────────────────┐   │   │
│  │  │  • championship_id (FK, INDEXED)                  │   │   │
│  │  │  • driver_code (TEXT, INDEXED)                    │   │   │
│  │  │  • position (INTEGER, INDEXED)                    │   │   │
│  │  │  • points (INTEGER)                               │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │  Indexes:                                                 │   │
│  │    • idx_winner                                          │   │
│  │    • idx_num_races                                       │   │
│  │    • idx_winner_num_races (composite)                    │   │
│  │    • idx_driver_position (driver_code, position)         │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                   ▲
                   │
                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Data Input (data/)                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │               championships.csv                           │   │
│  │  ┌───────────────────────────────────────────────────┐   │   │
│  │  │  Driver, 1, 2, 3, 4, ..., 24                      │   │   │
│  │  │  VER,   25,18,25,15, ..., 18                      │   │   │
│  │  │  NOR,   18,25,18,25, ..., 25                      │   │   │
│  │  │  ...                                               │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## 🔧 Component Breakdown

### 1. Application Factory (`__init__.py`)

**Purpose:** Creates and configures the Flask application

**Responsibilities:**
- Initialize Flask app with configuration
- Register blueprints (API, Views)
- Set up database connections
- Configure Swagger documentation
- Handle instance path configuration
- Set up error handlers

**Key Features:**
- Environment variable support (`DATABASE_PATH`, `DATA_FOLDER`)
- Flexible instance path (inside project, not parent dir)
- Dark mode CSS variable support
- Automatic folder creation

### 2. API Blueprint (`championship/api.py`)

**Purpose:** RESTful API endpoints for data access

**Endpoints:**
| Endpoint | Method | Description | Optimization |
|----------|--------|-------------|--------------|
| `/api/data` | GET | Paginated championship data | Limit/offset pagination |
| `/api/championship/<id>` | GET | Single championship details | Direct ID lookup |
| `/api/all_championship_wins` | GET | Championship wins per driver | Aggregation query |
| `/api/highest_position` | GET | Best position per driver | Smart heuristic + cache |
| `/api/head_to_head/<d1>/<d2>` | GET | Driver comparison | Filtered scan |
| `/api/min_races_to_win` | GET | Min races to win | Grouped by num_races |
| `/api/driver_positions?position=N` | GET | Position counts | Python aggregation |
| `/api/championship_win_probability` | GET | Win probability by races | Calculation + cache |
| `/api/create_championship` | POST | Find championship by rounds | Exact match on rounds |
| `/api/clear-cache` | POST | Clear API caches | Global cache reset |

**Performance Strategies:**
- **Caching:** Global in-memory cache for expensive queries
- **SQL Optimization:** Strategic use of indexes
- **Smart Heuristics:** Process from max races down
- **Early Termination:** Stop when optimal found
- **Lazy Loading:** Only fetch what's needed

### 3. Views Blueprint (`championship/views.py`)

**Purpose:** Render HTML pages for web interface

**Routes:**
- `/` - Homepage with endpoint list
- `/highest_position` - Best championship positions
- `/head_to_head` - Driver comparison form
- `/head_to_head_result` - Comparison results
- `/all_championship_wins` - Championship wins table
- `/championship/<id>` - Single championship details
- `/min_races_to_win` - Minimum races to win
- `/driver_positions` - Position distribution (interactive)
- `/championship_win_probability` - Win probability charts
- `/create_championship` - Find championship by rounds

### 4. Business Logic (`championship/logic.py`)

**Purpose:** Core championship calculations

**Functions:**
- `get_round_points_for_championship(drivers, round_numbers)` - Points per round
- `calculate_championship_from_rounds(round_numbers)` - Calculate standings from rounds

### 5. CLI Commands (`championship/commands.py`)

**Purpose:** Command-line interface for setup and data processing

**Commands:**

#### `flask setup`
- Creates `data/` and `instance/` folders
- Initializes database with PRAGMAs
- Creates sample CSV template
- Shows next steps

#### `flask init-db [--clear]`
- Creates database schema
- Applies performance PRAGMAs
- Creates indexes
- Optional: clears existing data

#### `flask process-data [--batch-size N]`
- Reads CSV data
- Generates all championship combinations (2^n - 1)
- Bulk inserts with transactions
- Configurable batch size for memory optimization

**Data Processing Algorithm:**
```python
for num_races in range(1, total_races + 1):
    for combination in combinations(races, num_races):
        standings = calculate_standings(combination)
        batch.append(standings)

        if len(batch) >= batch_size:
            db.executemany(INSERT, batch)
            batch = []
```

### 6. Database Layer (`db.py`)

**Purpose:** Database connection and initialization

**Key Functions:**

#### `get_db()`
- Returns SQLite connection from Flask `g` object
- Auto-creates instance directory if missing
- Connection pooling via Flask's request context

#### `init_db(clear_existing=False)`
- Creates `championship_results` table
- Creates `position_results` table for fast position queries
- Applies performance PRAGMAs:
  - `journal_mode=WAL` (Write-Ahead Logging)
  - `synchronous=NORMAL` (balance of speed/safety)
  - `temp_store=MEMORY` (temp tables in RAM)
  - `cache_size=-50000` (50MB cache)
  - `mmap_size=268435456` (256MB memory-mapped I/O)
- Creates indexes including `idx_driver_position` for fast P2-P20 queries
- Optional: clears database

#### `close_db()`
- Closes database connection on request teardown

### 7. Data Models (`championship/models.py`)

**Purpose:** Driver and round name mappings

**Contents:**
- `DRIVER_NAMES` - Full driver names
- `ROUND_NAMES` - Race location names (per season)

### 8. Error Handlers (`championship/errors.py`)

**Purpose:** Custom error pages

**Handlers:**
- 404 - Page Not Found
- 500 - Internal Server Error

## 📊 Data Flow

### Championship Processing Flow

```
CSV File → Pandas → NumPy → Combinations → SQLite
    ↓         ↓        ↓          ↓           ↓
Read CSV  Convert  Optimize  Generate   Bulk Insert
          types    arrays    combos     w/ transaction
```

**Steps:**
1. **Read CSV** - Load driver points from CSV
2. **Convert to NumPy** - Fast array operations
3. **Generate Combinations** - All possible race subsets
4. **Calculate Standings** - Sort by points for each combo
5. **Bulk Insert** - Transaction-based batch inserts

### API Request Flow

```
HTTP Request → Flask Router → Blueprint → Logic → Database → Response
      ↓            ↓             ↓          ↓        ↓          ↓
   Parse      Find route    Check cache   Query   Fetch    JSON/HTML
   params                   or compute     SQL    rows     response
```

## 🔒 Security Considerations

1. **SQL Injection Prevention**
   - Parameterized queries (`?` placeholders)
   - No string concatenation in SQL

2. **Input Validation**
   - Type checking on API parameters
   - Range validation (position, race numbers)

3. **Error Handling**
   - Custom error pages (no stack traces to users)
   - Graceful degradation

4. **Rate Limiting** (Future)
   - Consider adding for API endpoints

## ⚡ Performance Optimizations

### Database Level
- **WAL Mode** - Concurrent reads/writes
- **Memory-Mapped I/O** - OS-level caching
- **Indexes** - Strategic indexes on frequently queried columns
- **Batch Inserts** - Single transaction for millions of rows

### Application Level
- **In-Memory Caching** - Expensive query results cached
- **Smart Algorithms** - Heuristic-based searching
- **Early Termination** - Stop when optimal found
- **Lazy Loading** - Only fetch necessary data

### Frontend Level
- **Responsive Design** - Mobile-first CSS
- **Debounced API Calls** - Reduce server load
- **Optimistic UI** - Show loading states
- **Code Splitting** - Separate JS files

## 🧪 Testing Strategy (Future)

```
tests/
├── unit/
│   ├── test_logic.py          # Championship calculations
│   ├── test_api.py            # API endpoints
│   └── test_db.py             # Database operations
├── integration/
│   ├── test_data_processing.py # End-to-end data flow
│   └── test_api_integration.py # API integration tests
└── performance/
    └── test_benchmarks.py     # Performance benchmarks
```

## 📈 Scalability Considerations

### Current Scale
- **Data:** 16.7M championships (24 races)
- **Database Size:** ~1-2 GB
- **Response Time:** <1s (cached), <3s (uncached)

### Future Scale (30 races)
- **Data:** >1 billion championships
- **Database Size:** ~50-100 GB
- **Recommendations:**
  - Consider PostgreSQL for larger datasets
  - Implement Redis for distributed caching
  - Add background workers for data processing
  - Consider sharding by num_races

## 🔄 Deployment Architecture

```
┌─────────────┐
│   Nginx     │  ← Reverse Proxy
└──────┬──────┘
       │
┌──────▼──────┐
│   Gunicorn  │  ← WSGI Server (multiple workers)
└──────┬──────┘
       │
┌──────▼──────┐
│   Flask App │  ← Application
└──────┬──────┘
       │
┌──────▼──────┐
│   SQLite    │  ← Database
└─────────────┘
```

**Production Recommendations:**
- Gunicorn with 4-8 workers
- Nginx for static file serving
- Consider PostgreSQL for production
- Redis for session storage
- Monitoring (Sentry, New Relic)

## 🛠️ Development Workflow

```
1. Edit code → 2. Flask run → 3. Test locally → 4. Commit → 5. Push → 6. Deploy
     ↓              ↓              ↓              ↓          ↓          ↓
  VS Code      Auto-reload    Manual test      Git       GitHub    Production
```

## 📦 Dependencies

### Core
- **Flask** - Web framework
- **Pandas** - Data processing
- **NumPy** - Fast array operations
- **SQLite3** - Database (built-in)

### Extensions
- **Flasgger** - Swagger/OpenAPI documentation
- **python-dotenv** - Environment variable management

### Development
- **pytest** (future) - Testing framework
- **black** (future) - Code formatting
- **flake8** (future) - Linting

## 🔗 Integration Points

### External Services (Future)
- Formula 1 API for live data
- GitHub Actions for CI/CD
- Cloud storage for backups
- Analytics services

---

**Architecture Version:** 2.0
**Last Updated:** December 2025
**Maintainer:** NikoKiru
