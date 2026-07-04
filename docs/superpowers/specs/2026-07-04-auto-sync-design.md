# Auto-sync design — self-maintaining season data

**Date:** 2026-07-04
**Goal:** eliminate the manual data chores. Today the user must (a) notice a race
happened, (b) run `f1 fetch-race --season --round N` with the right N, (c) run
`f1 refresh-bio` to keep career stats fresh, (d) commit the data files, and (e)
hand-write `data/seasons/{YYYY}.json` every new season. All of it becomes
API-driven and one-command (or zero-command via CI).

## Feasibility (validated against the live Jolpica-F1 API, 2026-07-04)

| Need | Endpoint | Verified result |
| --- | --- | --- |
| Season schedule + dates | `GET /ergast/f1/{season}.json` | 22 rounds for 2026, dates, race names, `circuitId` |
| Sprint detection | same payload | `Sprint` block present on rounds 2, 4, 5, 9, 12, 16 — matches the app |
| Round numbering | same payload | Jolpica renumbered after the Bahrain/Saudi cancellations — **matches the app's sequential numbering exactly** |
| Latest completed round | `GET /{season}/last/results.json` | round 8 (Austria) — matches CSV |
| Season roster | `GET /{season}/drivers.json`, `/{season}/constructors.json`, `/{season}/constructors/{id}/drivers.json` | works; drivers include `code`, `permanentNumber`, `dateOfBirth`, `nationality`, `driverId` |
| Career totals | `MRData.total` count trick (already used by `refresh-bio`) | works |
| Championship titles across seasons | `/drivers/{id}/driverstandings/1.json` | **NOT supported** — Jolpica requires `season_year`. Titles stay hand-curated (they change once a year; the merge preserves them). |

## What gets built

### 1. `app/pipeline/rebuild.py` — shared rebuild chain
`fetch_race.py` and `add_race.py` duplicate the same 20-line chain (WDC writer →
stats → WCC builder → constructor stats). Extract `rebuild_season(settings,
season, echo)` and reuse it in both + the new sync command.

### 2. `jolpica_service.fetch_schedule(season)`
Returns a list of `ScheduleRound` dicts: `round`, `name`, `circuit_id`,
`country`, `date` (ISO), `has_sprint`. 404 / empty → `JolpicaError` /
`RoundNotFoundError` consistent with existing helpers. Plus
`fetch_season_drivers(season)` and `fetch_driver_constructor(season, driver_id)`
(for roster enrichment) and `fetch_driver_first_season(driver_id)` (debut year,
used by new-season scaffold).

### 3. `app/services/circuit_codes.py` + `app/services/flags.py`
Static maps: `circuitId → 3-letter round label` (covers every circuit used
2020–2026: albert_park→AUS, shanghai→CHN, …, madring→ESP) with fallback =
first 3 letters of the country, uppercased, plus a warning. Ergast demonym →
flag emoji ("Dutch"→🇳🇱) with 🏁 fallback.

### 4. `app/services/sync_service.py` — pure, unit-testable logic
- `merge_schedule(raw_json, schedule, raced_rounds)` → `(new_json, changes)`.
  Rules: **rounds already raced (present in CSV) are frozen**; future rounds are
  added/relabeled/removed to match the schedule (handles mid-season
  cancellations and renumbering); `sprint_rounds` = schedule sprints ∪ raced
  sprint rounds from the CSV; existing labels win over generated ones for raced
  rounds only.
- `plan_missing_rounds(schedule, csv_rounds, today)` → rounds with
  `date <= today` not yet in the CSV.
- `merge_counts(existing, fetched, now_iso)` → `(merged, changed)`. Preserves
  hand-curated keys (`championships`), and **only stamps `updated_at` when a
  value actually changed** — fixes the noisy no-op diffs `refresh-bio`
  produces today.
- `roster_gaps(csv_drivers, raw_json)` → driver codes in results that are
  missing from the season JSON (mid-season substitutes).

### 5. `f1 sync` — the one command
`f1 sync [--season YYYY] [--dry-run] [--no-reprocess] [--bio/--no-bio]`
1. Fetch schedule → merge calendar/sprint metadata into the season JSON.
2. Find completed rounds missing from the CSV → fetch each (race + sprint),
   splice via the existing `race_csv` module. "Results not posted yet" (404)
   skips gracefully.
3. Roster enrichment: any new driver code in the results gets a JSON stub from
   the API (name, number, flag, birthdate, jolpica_id, team via the driver's
   season constructor); unknown teams get a stub + warning.
4. Bio refresh: default **auto** (runs only when new rounds landed); `--bio`
   forces, `--no-bio` skips. Uses `merge_counts`, so no-change runs are no-ops.
5. If the CSV changed and reprocessing is enabled → `rebuild_season` once.
6. Idempotent: a re-run when up to date makes 1 API call and touches nothing.
   `--dry-run` prints the plan without writing.

### 6. `f1 new-season --season YYYY [--from-season YYYY-1] [--bio]`
Scaffolds `data/seasons/{YYYY}.json` from the API: rounds + sprint_rounds from
the schedule; teams and drivers from the season rosters. Colors, principal,
power_unit, chassis, and championship counts carry over from the previous
season's JSON (matched by `jolpica_id`); anything not carryable gets a default
plus a printed curation checklist. Degrades gracefully when Jolpica doesn't
have the season yet. Refuses to overwrite an existing JSON without `--force`.

### 7. `refresh-bio` churn fix
Switch to `merge_counts`; skip the file write entirely when nothing changed.

### 8. `.github/workflows/data-sync.yml` — zero-touch weekly update
Cron Monday 06:00 UTC (races end Sunday) + `workflow_dispatch`. Installs the
package, runs `f1 sync --no-reprocess` (data files only — no DB build in CI),
and auto-commits `data/` changes with the github-actions bot identity
(`permissions: contents: write`). The local machine then just needs `git pull`
+ the Tkinter **Build** button (or `f1 sync`) — consistent with the local-only
deploy story.

### 9. Tkinter manager: **Sync season** button
One click runs `python -m app.cli sync --season S` through the existing
subprocess/log plumbing. Sync chains everything, so no callback chain needed.

### 10. Doc/config hygiene (drift found during exploration)
- `README.md` + `data/README.md`: sprint-weekend lists still show the
  pre-renumbering rounds (2/6/7/11/14/18); actual metadata is 2/4/5/9/12/16.
  Rewrite the "keeping a live season current" flow around `f1 sync`.
- `.env.example` is still Flask-era (`FLASK_APP`, `SECRET_KEY`) — the app has
  been FastAPI + pydantic-settings for months. Rewrite with the real settings.
- CHANGELOG entry.

## Approaches considered

1. **`f1 sync` + CI cron (chosen)** — one idempotent command usable locally,
   by the Tkinter UI, and by CI. Repo data stays current with zero action.
2. **In-app background scheduler** — FastAPI task auto-rebuilds the DB.
   Rejected: multi-minute CPU-bound rebuild inside the web process, partial
   data mid-rebuild, surprise CPU spikes. The Tkinter manager is the ops surface.
3. **Windows Task Scheduler** — config lives outside the repo, not portable,
   invisible. Rejected in favor of CI cron + one-click local sync.

## Testing

Mirrors existing patterns (`httpx.MockTransport`, tmp-path settings fixture from
`test_cli.py`): schedule parsing; merge rules (frozen raced rounds, future
relabel/removal, sprint union); missing-round planning around `today`;
`merge_counts` churn behavior; sync CLI end-to-end against a mocked transport
(fetches missing round, updates JSON, dry-run writes nothing, up-to-date no-op);
new-season scaffold with carry-over; flag/circuit fallbacks.

## Out of scope

- Championship-title automation (API can't do it; preserved by merge).
- Auto-rebuild of the SQLite DB in CI (artifact too heavy; local rebuild stays).
- Publishing the `wiki/` folder (known-stale, separate concern).
- Team colors from an API (no reliable source; carried over per season).

## Execution note

Run autonomously per the user's request ("make everything more automatic…
only implement if possible"): implemented test-first in a feature branch,
committed locally, nothing pushed. The design doc doubles as the plan; phases
follow the numbered sections above.
