# F1 Season Calculator - Setup Guide

This guide will help you set up the F1 Season Calculator on a new machine.

## Quick Start

### 1. Install Dependencies

First, create a virtual environment and install the required packages:

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 2. Run Initial Setup

The application now includes an automated setup command that creates all necessary folders and files:

```powershell
flask setup
```

This command will:
- Create the `data/` folder if it doesn't exist
- Create the `instance/` folder for the database
- Initialize the database with optimized settings
- Create a sample CSV file (`data/championships_sample.csv`) as a template
- Display next steps

### 3. Add Your Championship Data

Create or copy your `championships.csv` file to the `data/` folder:

**Format:**
```csv
Driver,1,2,3,4,5
VER,25,18,25,15,18
NOR,18,25,18,25,25
LEC,15,15,15,18,15
```

- **First column:** Driver abbreviation (e.g., VER, NOR, LEC)
- **Subsequent columns:** Points for each race (numbered 1, 2, 3, ...)

### 4. Process the Data

Generate all championship combinations and save them to the database:

```powershell
flask process-data
```

Optional: Increase batch size for better performance on large datasets:
```powershell
flask process-data --batch-size 200000
```

### 5. Run the Application

```powershell
flask run
```

Access the application at:
- **Web Interface:** http://127.0.0.1:5000
- **API Documentation:** http://127.0.0.1:5000/apidocs

---

## What's Improved?

### Enhanced Database Initialization

The `init_db()` function now includes:

1. **Automatic Directory Creation**
   - Creates `instance/` folder automatically if it doesn't exist
   - Creates database directory structure as needed

2. **Better Error Handling**
   - Clear error messages if directories can't be created
   - Validation of database path and permissions

3. **Enhanced Performance Settings**
   - All existing PRAGMAs (WAL mode, cache tuning, etc.)
   - Added `mmap_size` for memory-mapped I/O (256MB)
   - Better transaction handling

4. **Improved Logging**
   - Shows database location
   - Indicates if database already exists
   - Displays current row count after initialization
   - Progress messages for each step

5. **Clear Database Option**
   - New `--clear` flag to reset the database:
     ```powershell
     flask init-db --clear
     ```

### New Setup Command

A new `flask setup` command that:
- Creates all necessary directories
- Validates folder structure
- Creates a sample CSV template
- Initializes the database
- Provides clear next steps

### Flexible Configuration

The application now supports environment variables for custom paths:

**Environment Variables:**
- `DATABASE_PATH` - Custom database file location
- `DATA_FOLDER` - Custom data folder location
- `SECRET_KEY` - Custom secret key (important for production!)

**Example `.env` file:**
```env
DATABASE_PATH=D:\F1Data\championships.db
DATA_FOLDER=D:\F1Data\csv_files
SECRET_KEY=your-secret-key-here
```

### Improved Commands

**`flask init-db`**
- Creates instance folder automatically
- Shows clear progress messages
- Optional `--clear` flag to reset database
- Displays database location and row count

**`flask process-data`**
- Validates CSV file exists before processing
- Shows file path and batch size
- Better error messages
- Optional `--batch-size` parameter
- Cleaner output with progress indicators

**`flask setup` (NEW)**
- One-command setup for new installations
- Creates all necessary folders
- Generates sample CSV template
- Runs database initialization
- Provides step-by-step guidance

---

## Common Scenarios

### Setting Up on a New PC (Your Case!)

1. Clone the repository
2. Create virtual environment and install dependencies
3. Run `flask setup`
4. Copy your CSV data to `data/championships.csv`
5. Run `flask process-data`
6. Run `flask run`

### Using Custom Paths

If you want to store data/database in different locations:

1. Create a `.env` file (copy from `.env.example`)
2. Set custom paths:
   ```env
   DATABASE_PATH=E:\MyF1Data\championships.db
   DATA_FOLDER=E:\MyF1Data\csv_files
   ```
3. Run `flask setup`
4. Continue with normal workflow

### Resetting the Database

To clear and reinitialize the database:

```powershell
flask init-db --clear
flask process-data
```

### Checking Current Configuration

To see where your data folder and database are located, run any Flask command with verbose output, or check the output of `flask setup`.

---

## Troubleshooting

### "CSV file not found" Error

If you see this error when running `flask process-data`:
1. Make sure you've run `flask setup` first
2. Check that `data/championships.csv` exists
3. Verify the file format matches the expected structure

### "Instance folder doesn't exist" Error

This should no longer happen with the improvements, but if it does:
1. Run `flask setup` to create all necessary folders
2. Manually create the `instance/` folder if needed

### Permission Errors

If you get permission errors when creating folders:
1. Check you have write permissions in the project directory
2. Try running the command as administrator (not recommended)
3. Use custom paths via environment variables to a location you control

### Virtual Environment Not Activated

If you get "flask: command not found":
1. Make sure you've created the virtual environment
2. Activate it: `.venv\Scripts\Activate.ps1` (PowerShell)
3. Install dependencies: `pip install -r requirements.txt`

---

## Performance Notes

- Database uses WAL mode for better concurrent access
- Memory-mapped I/O (256MB) for faster reads
- Optimized cache size (50MB)
- Bulk inserts with configurable batch size
- Indexes on frequently queried columns

For very large datasets (20+ races), consider increasing the batch size:
```powershell
flask process-data --batch-size 200000
```

---

## Next Steps

After setup:
1. Explore the web interface at http://127.0.0.1:5000
2. Check API documentation at http://127.0.0.1:5000/apidocs
3. Try different API endpoints to analyze your championship data
4. Modify `championships.csv` and reprocess to update results

Enjoy analyzing your F1 championship scenarios!
