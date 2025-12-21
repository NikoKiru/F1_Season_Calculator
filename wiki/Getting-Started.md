# Getting Started

Get up and running with F1 Season Calculator in under 5 minutes.

## Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- Git

## Quick Start

```bash
# Clone the repository
git clone https://github.com/NikoKiru/F1_Season_Calculator.git
cd F1_Season_Calculator

# Create and activate virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize the application
flask setup

# Run the server
flask run
```

Open your browser to **http://127.0.0.1:5000**

## First Steps

### 1. Browse Championships

Navigate to the home page to see a list of all available F1 seasons. Click on any year to explore that championship.

### 2. Explore Race Combinations

On a championship page, you'll see:
- Current standings
- Race selection interface
- Statistical analysis

Use the checkboxes to select different race combinations and see how standings would change.

### 3. View Statistics

Each championship page includes:
- **Season Progression Chart**: Visual representation of points accumulation
- **Head-to-Head**: Direct comparisons between drivers
- **Position Distribution**: How often each driver finished in each position

### 4. Use the API

Access the REST API at `/api/` or explore it interactively at `/apidocs/`.

Example API call:
```bash
curl http://127.0.0.1:5000/api/data?year=2024
```

## Next Steps

- [[Installation]] - Detailed installation options
- [[Features]] - Complete feature documentation
- [[API Reference]] - Full API documentation
