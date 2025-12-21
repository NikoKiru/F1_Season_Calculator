# Architecture

Technical architecture overview of F1 Season Calculator.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Client                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Browser    │  │   API Client │  │   CLI        │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Flask Application                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    Views     │  │     API      │  │   Commands   │       │
│  │  (routes)    │  │  (endpoints) │  │    (CLI)     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│                              │                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │                    Logic Layer                     │      │
│  │         (calculations, data processing)            │      │
│  └───────────────────────────────────────────────────┘      │
│                              │                               │
│  ┌───────────────────────────────────────────────────┐      │
│  │                   Data Layer                       │      │
│  │              (models, database)                    │      │
│  └───────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  ┌──────────────┐                    ┌──────────────┐       │
│  │   SQLite     │                    │  Ergast API  │       │
│  │   Database   │                    │  (external)  │       │
│  └──────────────┘                    └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
F1_Season_Calculator/
├── app.py                 # Application entry point
├── db.py                  # Database initialization
├── championship/          # Core application package
│   ├── __init__.py       # Blueprint registration
│   ├── api.py            # REST API endpoints
│   ├── views.py          # Web routes (HTML pages)
│   ├── commands.py       # CLI commands
│   ├── logic.py          # Business logic & calculations
│   ├── models.py         # Data models
│   └── errors.py         # Error handlers
├── static/               # Frontend assets
│   ├── js/              # JavaScript files
│   └── style.css        # Stylesheets
├── templates/            # Jinja2 HTML templates
├── tests/                # Test suite
├── docs/                 # Documentation
└── instance/             # Instance-specific files (database)
```

## Component Details

### Application Entry Point (`app.py`)

- Creates Flask application instance
- Registers blueprints
- Configures application settings
- Initializes database connection

### Championship Package

#### `api.py` - REST API

Provides JSON endpoints for programmatic access.

**Key Features**:
- RESTful design
- Swagger/OpenAPI documentation
- Response caching
- Input validation

**Caching Strategy**:
```python
_cache = {}  # Module-level cache

def get_data(year):
    if year not in _cache:
        _cache[year] = calculate_data(year)
    return _cache[year]
```

#### `views.py` - Web Routes

Renders HTML pages using Jinja2 templates.

**Routes**:
- `/` - Home page (season list)
- `/championship/<year>` - Championship details

#### `commands.py` - CLI Commands

Flask CLI extensions for administrative tasks.

**Commands**:
- `flask setup` - Full initialization
- `flask init-db` - Database schema
- `flask process-data` - Fetch external data

#### `logic.py` - Business Logic

Core calculation engine using NumPy for performance.

**Key Functions**:
- Standings calculation
- Points aggregation
- Statistical analysis
- Race subset filtering

#### `models.py` - Data Models

Data structures and database queries.

**Models**:
- Championship results
- Driver information
- Race metadata

### Database Layer (`db.py`)

SQLite database management.

**Schema**:
```sql
CREATE TABLE championship_results (
    id INTEGER PRIMARY KEY,
    year INTEGER,
    driver TEXT,
    race TEXT,
    position INTEGER,
    points REAL,
    is_sprint INTEGER
);
```

## Data Flow

### Page Request Flow

```
1. Browser requests /championship/2024
2. views.py handles route
3. logic.py calculates standings
4. models.py fetches from database
5. Template renders with data
6. HTML returned to browser
```

### API Request Flow

```
1. Client requests /api/data?year=2024
2. api.py handles endpoint
3. Check cache for existing data
4. If miss: logic.py calculates
5. Cache result
6. Return JSON response
```

### Data Initialization Flow

```
1. flask setup command
2. init-db creates schema
3. process-data fetches from Ergast API
4. Data transformed and stored
5. Cache cleared
```

## Technology Choices

### Flask

Chosen for:
- Lightweight and flexible
- Easy to understand
- Large ecosystem
- Excellent documentation

### SQLite

Chosen for:
- Zero configuration
- Single file database
- Sufficient for read-heavy workload
- Easy deployment

### NumPy

Chosen for:
- Fast array operations
- Efficient memory usage
- Vectorized calculations

### Chart.js

Chosen for:
- No build step required
- Responsive by default
- Good documentation
- Customizable styling

## Performance Considerations

### Caching

- In-memory caching for API responses
- Reduces database queries
- Cleared on data updates

### Database Indexing

```sql
CREATE INDEX idx_year ON championship_results(year);
CREATE INDEX idx_driver ON championship_results(driver);
```

### Calculation Optimization

- NumPy vectorized operations
- Lazy loading where possible
- Efficient data structures

## Security

### Input Validation

- Year parameter validated
- Driver codes sanitized
- SQL injection prevented via parameterized queries

### Error Handling

- Custom error handlers
- No sensitive data in error messages
- Proper HTTP status codes

## Testing Architecture

```
tests/
├── conftest.py         # Shared fixtures
├── test_api.py         # API endpoint tests
├── test_logic.py       # Business logic tests
└── test_views.py       # View tests
```

**Testing Strategy**:
- Unit tests for logic functions
- Integration tests for API endpoints
- Fixture-based database setup
- Cache isolation between tests

## Deployment

See [[CI-CD]] for deployment pipeline details.

### Production Recommendations

1. Use gunicorn or uWSGI as WSGI server
2. Put behind nginx reverse proxy
3. Enable HTTPS
4. Set `FLASK_ENV=production`
5. Configure proper logging
