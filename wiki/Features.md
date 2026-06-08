# Features

Complete overview of F1 Season Calculator features.

## Championship Analysis

### Race Combination Calculator

The core feature of F1 Season Calculator. Select any subset of races from a season to see alternative championship standings.

**Use Cases**:
- What if a driver missed certain races?
- How would standings look with only European races?
- Championship impact of specific race results

**How to Use**:
1. Navigate to a championship year
2. Use checkboxes to select/deselect races
3. View recalculated standings in real-time

### Season Progression Chart

Interactive line chart showing cumulative points throughout the season.

**Features**:
- Team-colored lines for each driver
- Dashed lines for lower-scoring teammates
- Top 5 drivers displayed for clarity
- Hover for detailed point values

### Head-to-Head Comparisons

Direct statistical comparison between any two drivers.

**Metrics Compared**:
- Total points
- Race wins
- Podium finishes
- Average finishing position
- Head-to-head race results

### Position Distribution

Heatmap showing how often each driver finished in each position.

**Insights Provided**:
- Consistency analysis
- Peak performance identification
- DNF patterns

### Driver Statistics

Comprehensive statistics for each driver in a season.

**Statistics Include**:
- Total points
- Wins, podiums, top-10 finishes
- Best/worst finishing positions
- Points per race average
- Sprint race performance (where applicable)

### Notable Scenarios

A curated "hall of fame of what-ifs" — the most extreme championships hiding in
the season's race combinations. Reachable from **Championships ▾ → Notable
Scenarios** (and `GET /api/statistics/notable-scenarios`).

**Cards**:
- **The Nail-Biter** — the closest title: smallest points gap between champion
  and runner-up (a zero gap means it was decided on countback).
- **The Demolition** — the biggest winning margin of any scenario.
- **Against All Odds** — the most rounds you can count and still crown someone
  other than the real season champion.
- **The Cinderella Story** — the rarest champion: the driver who takes the
  title in the fewest scenarios.
- **The Kingmaker** — the single round that swings the title in the most
  scenarios, with the biggest before/after flip.

Each card links straight to that championship's full breakdown. The data is
**precomputed** during `f1 compute-stats` (alongside the other statistics
caches), so it stays an instant lookup no matter how large the season grows.

## Data Management

### Automatic Data Fetching

Data is automatically fetched from the Ergast F1 API.

**Supported Data**:
- Race results (1950-present)
- Sprint race results (2021-present)
- Driver information
- Constructor information
- Points systems per era

### Local Database

All data is cached locally in SQLite for fast access.

**Benefits**:
- Offline capability after initial fetch
- Fast query performance
- No API rate limiting concerns

## API Access

### REST API

Full programmatic access to all calculations.

**Endpoints**:
- `/api/data` - Championship data
- `/api/highest-position` - Best finishes
- `/api/head-to-head` - Driver comparisons
- `/api/driver-positions` - Position distributions
- `/api/driver-stats` - Comprehensive statistics

See [[API Reference]] for complete documentation.

### Swagger UI

Interactive API explorer available at `/apidocs/`.

**Features**:
- Try endpoints directly in browser
- View request/response schemas
- Copy curl commands

## User Interface

### Responsive Design

Works on desktop, tablet, and mobile devices.

### Dark Mode Support

Respects system color scheme preferences.

### Print-Friendly

Championship tables can be printed or exported.

## Performance

### Caching

API responses are cached for improved performance.

**Cache Behavior**:
- Cleared on data refresh
- Per-endpoint caching
- Memory-efficient implementation

### Optimized Calculations

NumPy-based calculations for fast processing of large datasets.

## Extensibility

### Modular Architecture

Clean separation of concerns allows easy extension.

**Extension Points**:
- Add new statistics calculations
- Create custom visualizations
- Integrate additional data sources

See [[Architecture]] for technical details.
