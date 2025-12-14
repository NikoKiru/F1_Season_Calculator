# Quick Start - New PC Setup

## You're here because you cloned your repo to a new PC ✅

The code ran on your original PC but the `data/` and `instance/` folders were in different locations. **This is now fixed!**

## What to Do Now (5 Simple Steps)

### Step 1: Create Virtual Environment
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Run Automated Setup
```powershell
flask setup
```
This creates all folders, the database, and a sample CSV template.

### Step 4: Add Your Championship Data
Copy or create your `championships.csv` file in the `data/` folder:
```csv
Driver,1,2,3,4,5
VER,25,18,25,15,18
NOR,18,25,18,25,25
LEC,15,15,15,18,15
```

### Step 5: Process Data & Run
```powershell
flask process-data
flask run
```

Access at: http://127.0.0.1:5000

---

## What Changed?

### ✅ Auto-creates missing folders
No more manually creating `data/` and `instance/` folders!

### ✅ Better error messages
If something's missing, you'll know exactly what and how to fix it.

### ✅ Sample CSV template
A `championships_sample.csv` is created to show you the format.

### ✅ Flexible paths
Want to store data elsewhere? Use environment variables:
```powershell
$env:DATA_FOLDER = "D:\MyF1Data"
$env:DATABASE_PATH = "D:\MyF1Data\championships.db"
flask setup
```

### ✅ Database reset option
```powershell
flask init-db --clear  # Start fresh
```

---

## Common Commands

| Command | What it does |
|---------|--------------|
| `flask setup` | One-time setup: creates folders, database, sample CSV |
| `flask init-db` | Initialize/update database schema |
| `flask init-db --clear` | Reset database (deletes all data) |
| `flask process-data` | Generate all championship combinations |
| `flask process-data --batch-size 200000` | Process with larger batch size |
| `flask run` | Start the web application |

---

## If You Have Issues

1. **"flask: command not found"**
   - Virtual environment not activated
   - Run: `.venv\Scripts\Activate.ps1`

2. **"CSV file not found"**
   - Run `flask setup` first
   - Make sure `data/championships.csv` exists

3. **Want to use different paths?**
   - Copy `.env.example` to `.env`
   - Edit the paths in `.env`
   - Run `flask setup`

---

## Files You Can Ignore
- `IMPROVEMENTS.md` - Technical details of what was improved
- `SETUP_GUIDE.md` - Comprehensive documentation
- This file (`QUICKSTART.md`) - You're reading it!

## Next Steps After Setup
1. Visit http://127.0.0.1:5000 for the web interface
2. Visit http://127.0.0.1:5000/apidocs for API documentation
3. Start analyzing your F1 championship scenarios!

---

**That's it! You're good to go! 🏎️**
