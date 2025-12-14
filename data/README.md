# Data Folder

This folder contains the championship data CSV files.

## Required File

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
