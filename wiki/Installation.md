# Installation

Detailed installation instructions for F1 Season Calculator.

## System Requirements

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11+ |
| RAM | 512 MB | 1 GB |
| Disk Space | 100 MB | 500 MB |

## Installation Methods

### Method 1: Standard Installation

```bash
# Clone repository
git clone https://github.com/NikoKiru/F1_Season_Calculator.git
cd F1_Season_Calculator

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup application
flask setup
```

### Method 2: Development Installation

For contributors who want to modify the code:

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/F1_Season_Calculator.git
cd F1_Season_Calculator

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or Windows equivalent

# Install in editable mode
pip install -e .

# Install development dependencies
pip install pytest pytest-cov black flake8

# Setup application
flask setup

# Verify installation
pytest
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_APP` | Application entry point | `app.py` |
| `FLASK_ENV` | Environment mode | `production` |
| `FLASK_DEBUG` | Enable debug mode | `0` |
| `DATABASE` | Database file path | `instance/f1_database.db` |

### Setting Environment Variables

**Windows (PowerShell)**:
```powershell
$env:FLASK_DEBUG = "1"
```

**Linux/Mac**:
```bash
export FLASK_DEBUG=1
```

## Running the Application

### Development Server

```bash
flask run
```

The server starts at `http://127.0.0.1:5000`

### Debug Mode

```bash
flask run --debug
```

### Custom Host/Port

```bash
flask run --host=0.0.0.0 --port=8080
```

## CLI Commands

F1 Season Calculator provides several CLI commands:

| Command | Description |
|---------|-------------|
| `flask setup` | Initialize database and fetch data |
| `flask init-db` | Initialize database schema |
| `flask process-data` | Fetch and process F1 data |

### Examples

```bash
# Full setup (recommended for first run)
flask setup

# Reinitialize database only
flask init-db

# Refresh data from API
flask process-data
```

## Verifying Installation

After installation, verify everything works:

```bash
# Run tests
pytest

# Start server and check endpoints
flask run &
curl http://127.0.0.1:5000/
curl http://127.0.0.1:5000/apidocs/
```

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'flask'`
**Solution**: Ensure virtual environment is activated

**Issue**: Database errors on startup
**Solution**: Run `flask setup` to initialize the database

**Issue**: Port 5000 already in use
**Solution**: Use a different port: `flask run --port=8080`

See [[FAQ]] for more troubleshooting tips.
