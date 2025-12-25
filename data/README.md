# Data Folder

This folder contains championship data and season configuration files.

## Directory Structure

```
data/
├── championships.csv         # Race results data (required)
├── championships_sample.csv  # Sample template
├── seasons/                  # Season configuration
│   └── 2025.json            # 2025 season config
└── README.md                # This file
```

## Championship Data

Create a `championships.csv` file with the following format:

```csv
Driver,1,2,3,4,5
VER,25,18,25,15,18
NOR,18,25,18,25,25
LEC,15,15,15,18,15
```

### Format Details:
- **First column:** Driver abbreviation (e.g., VER, NOR, LEC)
- **Subsequent columns:** Points for each race (numbered 1, 2, 3, ...)

## Season Configuration

Season data (drivers, teams, races) is stored in JSON files under `seasons/`.

### File Format: `seasons/{year}.json`

```json
{
    "season": 2025,
    "teams": {
        "McLaren": {"color": "#F47600"},
        "Red Bull Racing": {"color": "#4781D7"},
        "Mercedes": {"color": "#00D7B6"}
    },
    "drivers": {
        "VER": {
            "name": "Max Verstappen",
            "team": "Red Bull Racing",
            "number": 1,
            "flag": "🇳🇱"
        },
        "NOR": {
            "name": "Lando Norris",
            "team": "McLaren",
            "number": 4,
            "flag": "🇬🇧"
        }
    },
    "rounds": {
        "1": "AUS",
        "2": "CHN",
        "3": "JPN"
    }
}
```

### Adding a New Season

1. Create a new JSON file: `seasons/{year}.json`
2. Add all teams with their official colors
3. Add all drivers with their team, number, and flag
4. Add all race rounds with their abbreviations

The application loads the default season (2025) at startup. The season configuration is used to display driver names, team colors, and race names throughout the UI.

## Sample File

A `championships_sample.csv` file is provided as a template. You can:
1. Rename it to `championships.csv` and edit it with your data
2. Use it as a reference to create your own `championships.csv`

## Processing Data

After creating your `championships.csv` file, run:
```powershell
flask process-data
```

This will generate all possible championship combinations and save them to the database.
