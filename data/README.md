# Data Folder

Championship results and season configuration live here. Everything else
(combinations, statistics, position tables) is derived from these files.

## Layout

```
data/
├── championships_{YYYY}.csv    # Race + sprint results per season
├── championships_sample.csv    # Template
├── seasons/
│   └── {YYYY}.json             # Drivers, teams, rounds, sprint metadata
└── README.md
```

## CSV format

Column 1 is the 3-letter driver code. Each round gets one numeric column —
`1`, `2`, `3`, … — holding race points.

### Sprint weekends

Sprint weekends use a **paired column** layout: the race column `N` is
followed immediately by a sprint column `Ns`. Both belong to the same
weekend; selecting round `N` in a championship includes both race and
sprint points.

```csv
Driver,1,2,2s,3,6,6s
VER,25,18,8,25,25,7
NOR,18,25,6,18,18,8
LEC,15,15,4,15,15,5
```

In this example: rounds 1, 3 are plain races; rounds 2 and 6 are sprint
weekends. Round 2's total points for VER = `18 + 8 = 26`.

Constraints:
- Sprint scoring is 1st–8th: 8, 7, 6, 5, 4, 3, 2, 1 points.
- Drivers missing from a round are implicitly 0 points.
- Round numbers do **not** need to be contiguous — canceled rounds are
  simply omitted (see 2026 below).
- Every `Ns` column must be preceded by a matching `N` race column.

### Canceled rounds (2026)

Bahrain and Saudi Arabia were canceled for 2026. Jolpica renumbered the
remaining calendar to 22 sequential rounds and this repo follows that
numbering (round 4 = Miami, round 5 = Canada, …). If a future round is
canceled mid-season, `f1 sync` re-aligns the not-yet-raced rounds with
the API automatically; rounds that already have results are never
renamed or removed.

## Season configuration

```json
{
  "season": 2026,
  "teams": {
    "McLaren": {"color": "#F47600"},
    "Red Bull Racing": {"color": "#4781D7"}
  },
  "drivers": {
    "VER": {"name": "Max Verstappen", "team": "Red Bull Racing", "number": 1, "flag": "🇳🇱"}
  },
  "rounds": {
    "1": "AUS",
    "2": "CHN",
    "3": "JPN"
  },
  "sprint_rounds": [2, 6, 7, 11, 14, 18]
}
```

- `rounds` maps round number → short name. Omit canceled rounds entirely.
- `sprint_rounds` is the list of rounds that run a sprint session. Used
  only for UI affordances (the badge on round chips); the source of truth
  for sprint *points* is the CSV's `Ns` columns.

2026 sprint weekends (renumbered calendar): **2 (China), 4 (Miami),
5 (Canada), 9 (Silverstone), 12 (Zandvoort), 16 (Singapore)**.

Both `rounds` and `sprint_rounds` are maintained automatically by
`f1 sync`; hand-edit only when you want a custom label for a round that
has already been raced (sync never touches those).

## Populating data

**Automatically (recommended):**
```bash
f1 sync --season 2026
```
Fetches the calendar and every completed-but-missing round from the
Jolpica-F1 API, updates this folder, and rebuilds the database. A
scheduled GitHub Action does the same twice a week (data files only),
so after `git pull` the CSV/JSON here are usually already current.

**Manually from a scoreboard:**
```bash
f1 add-race --season 2026 --race 3 --results "VER:25,NOR:18,LEC:15" \
            --sprint  "VER:8,NOR:7,LEC:6"
```
`--sprint` is optional; supply it on sprint weekends only.

**From the Jolpica-F1 API (Ergast-compatible):**
```bash
f1 fetch-race --season 2026 --round 3
```
Pulls both race and sprint results and splices them into the CSV. Use
`--no-reprocess` to skip the full recompute (handy when batching multiple
rounds — reprocess once at the end with `f1 process-data --season 2026`).

Both commands rewrite the season CSV; if the season had already been
processed, the full combinator re-runs automatically.
