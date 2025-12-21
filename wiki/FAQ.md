# Frequently Asked Questions

Common questions and answers about F1 Season Calculator.

## General

### What seasons are supported?

All F1 seasons from 1950 to present. Data is fetched from the Ergast F1 API.

### How accurate is the data?

Data comes from the official Ergast F1 API, which is widely recognized as a reliable source for historical F1 data.

### Does it include sprint races?

Yes, sprint race results are included for seasons 2021 and later.

### How often is data updated?

Data is fetched when you run `flask setup` or `flask process-data`. Run these commands to get the latest race results.

---

## Installation

### What Python version do I need?

Python 3.10 or higher. Tested on 3.10, 3.11, and 3.12.

### Do I need to install a database?

No, the application uses SQLite which is included with Python. The database file is created automatically.

### Can I run it on Windows/Mac/Linux?

Yes, F1 Season Calculator works on all major operating systems.

### How do I update to the latest version?

```bash
cd F1_Season_Calculator
git pull origin main
pip install -r requirements.txt
flask setup  # If data schema changed
```

---

## Usage

### How do I calculate alternative standings?

1. Navigate to a championship year
2. Use the checkboxes to select/deselect races
3. The standings recalculate automatically

### Can I export the data?

Currently, you can:
- Use the API to get JSON data
- Print/save the webpage
- Access the SQLite database directly

### What do the dashed lines in the chart mean?

Dashed lines represent teammates who scored fewer points than their partner. Solid lines are for the higher-scoring teammate.

### Why are only 5 drivers shown in the chart?

For readability, only the top 5 drivers are displayed. This prevents the chart from becoming cluttered.

---

## API

### Is authentication required?

No, the API is open for local use. No authentication needed.

### Is there rate limiting?

No rate limiting for local use. For production deployments, implement rate limiting at the reverse proxy level.

### How do I access the API documentation?

Navigate to `/apidocs/` in your browser for interactive Swagger documentation.

### Can I use the API from other applications?

Yes, the REST API returns JSON and can be consumed by any HTTP client.

---

## Technical

### Where is the database stored?

The SQLite database is stored at `instance/f1_database.db`.

### How do I clear the cache?

```bash
# Via API
curl -X POST http://127.0.0.1:5000/api/clear-cache

# Or restart the application
```

### Can I use a different database?

The application is designed for SQLite. Using a different database would require code modifications.

### How do I run in production?

Recommended setup:
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Use with nginx as a reverse proxy.

---

## Troubleshooting

### Application won't start

**Common causes**:
1. Virtual environment not activated
2. Dependencies not installed
3. Database not initialized

**Solution**:
```bash
source .venv/bin/activate  # or Windows equivalent
pip install -r requirements.txt
flask setup
flask run
```

### "No such table" error

The database schema hasn't been initialized.

**Solution**:
```bash
flask init-db
flask process-data
```

### Port 5000 already in use

Another application is using port 5000.

**Solution**:
```bash
flask run --port=8080
```

Or find and stop the conflicting process.

### Data seems outdated

The data needs to be refreshed.

**Solution**:
```bash
flask process-data
```

### Tests failing locally

**Common causes**:
1. Dependencies missing
2. Database not set up
3. Cache pollution

**Solution**:
```bash
pip install pytest pytest-cov
flask setup
pytest -v
```

### Chart not displaying

**Common causes**:
1. JavaScript error
2. No data for selected races
3. Browser compatibility

**Solution**:
1. Check browser console for errors
2. Ensure at least one race is selected
3. Try a modern browser (Chrome, Firefox, Edge)

---

## Contributing

### How do I report a bug?

Open an issue on [GitHub Issues](https://github.com/NikoKiru/F1_Season_Calculator/issues) using the bug report template.

### How do I request a feature?

Open an issue with the feature request template. Describe the feature and why it would be useful.

### Do I need to sign a CLA?

No Contributor License Agreement is required. Contributions are accepted under the MIT License.

### How long until my PR is reviewed?

Maintainers aim to review PRs within a week. Complex changes may take longer.

---

## Data & Privacy

### Does this application collect data?

No, F1 Season Calculator runs entirely locally and does not collect or transmit user data.

### What external services are used?

Only the Ergast F1 API for fetching race data. This happens only when you explicitly run data commands.

### Can I use this for commercial purposes?

Check the MIT License terms. The F1 data from Ergast has its own terms of use.

---

## Still Have Questions?

- Check [GitHub Issues](https://github.com/NikoKiru/F1_Season_Calculator/issues) for similar questions
- Open a [Discussion](https://github.com/NikoKiru/F1_Season_Calculator/discussions)
- Review the [[Home|Wiki documentation]]
