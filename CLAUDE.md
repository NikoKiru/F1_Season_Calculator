# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Scores every possible F1 championship: for a season of N raced weekends it generates all 2^N-1 subsets ("what if only these rounds counted?") and serves the results. Almost everything the site shows is precomputed by a batch pipeline, so most logic lives there rather than in request handlers.

## Commands

Run from the repo root with the venv active, or call `.venv\Scripts\<tool>` directly on Windows.

```bash
pip install -e ".[dev]"                     # backend plus pytest, ruff, mypy, playwright
cd web && npm ci && npm run build           # frontend, output goes to app/static/dist/
uvicorn "app.main:create_app" --factory --host 127.0.0.1 --port 8000 --reload

f1 sync                                     # fetch new results from Jolpica, rebuild if needed
f1 sync --dry-run                           # show the plan, write nothing

pytest                                      # unit, API and e2e
pytest tests/unit/test_pipeline.py          # one file
pytest tests/unit/test_rebuild.py::test_changed_csv_makes_the_season_stale   # one test

# What CI enforces
ruff check app tests
pytest tests/unit tests/api --cov=app --cov-fail-under=70
cd web && npm run typecheck && npm run build
```

- E2e tests skip silently unless the browser is installed: `playwright install chromium`.
- `mypy app` is configured as strict but is not in CI and has about 180 existing errors. Don't add new ones.
- `web/` needs Node 20.19+ or 22.12+. `web/.npmrc` makes npm refuse anything older.

## Architecture

### Data flow

The sources of truth are `data/championships_{YYYY}.csv` (points per round, see `data/README.md`) and `data/seasons/{YYYY}.json` (calendar, roster, colors, career stats). Both are tracked in git. `instance/championships.db` is gitignored and fully derived, so it can always be rebuilt.

`app/pipeline/rebuild.py::rebuild_season` is the single regeneration path, used by `sync`, `add-race` and `fetch-race`: combinator → `writer` → `stats_compute`, then `constructor_builder` → `constructor_writer` → `constructor_stats_compute`.

A finished rebuild stamps the CSV's SHA-256 into `season_builds` as its last step, and `clear_season` removes the stamp. `f1 sync` rebuilds whenever `rebuild.is_current` is false, which covers new results, a `git pull` and an interrupted build. `sync` writes data files only after all fetches succeed, so an interrupted run is simply redone. The Tkinter manager's **Build** button (`tools/manage_ui.py`) runs the CLI steps separately and leaves no stamp, so the next `f1 sync` rebuilds once more.

### Scale

Row counts double with every round. At 18 rounds: 262,143 championships per table, 6M `position_results` rows, 0.9 GB, about 4 minutes to rebuild. A 24-round season is 64 times that. So:

- Treat a full rebuild as expensive and don't run one casually.
- Don't aggregate over `position_results` per request. Add a precomputed cache table in `stats_compute` instead, as `driver_head_to_head` and `driver_position_distribution` do.
- Position lists depend on insert order. The writers add rows in `championship_id` order and ids run shortest scenario first, so `ORDER BY rowid DESC` returns the longest scenarios from the index with no sort. Keep the writers sequential, or those lists lose their order.
- Lists can filter by season length only at P1, where `winner` is indexed and `win_probability_cache` has the count. Other positions would need a new per-length cache table and a rebuild.

### Ranking

`combinator.rank_standings` orders by points, then countback, then array (CSV) order. `countback_weights` encodes each scoring position as one digit of a base-(races + 1) number, which keeps the weights additive across any subset and the sort vectorized. Don't replace it with a per-subset Python loop.

Subsets select weekends, so a round's race and sprint points always travel together, but countback uses race results only. The CSV stores points rather than positions, so countback can't see past P10.

### Drivers and constructors are mirrored

The WDC and WCC sides are parallel implementations: `writer` / `constructor_writer`, `stats_compute` / `constructor_stats_compute`, `driver_service` / `constructor_service`, `championship_results` / `constructor_championship_results`, and so on. A change to one side usually belongs on the other too. Constructor scores are derived from the driver CSV using each driver's team in the season JSON, which is static for the whole season.

### Request path

`app/api/*` (JSON) and `app/views/pages.py` (Jinja SSR) both go through `app/services/*`, which call the raw SQL in `app/data/queries/*`. `SeasonDep` resolves `?season=`, defaulting to the newest season JSON. `championship_id` is unique across seasons and follows `race_combinations` order within one.

### In-process caches

Three caches live in the server process and nothing invalidates them when data changes:

| Cache | Where | Refresh |
|---|---|---|
| Service results (1 hour TTL) | `app/cache/service.py` | Restart, or `POST /api/admin/clear-cache` |
| Season JSON | `season_service` `lru_cache` | Restart |
| Vite manifest | `app/templating.py` `lru_cache` | Restart |

Restart the server after a rebuild, a season JSON edit or a frontend build, otherwise it serves stale data or asset URLs that no longer exist.

### Frontend

Each interactive page has one entry in `web/src/pages/`. A new entry must be listed in `rollupOptions.input` in `web/vite.config.ts` and loaded by its template with `vite_script("src/pages/x.ts")`. A missing `app/static/dist/manifest.json` raises no error: pages still render, but without styles or scripts.

### Schema

`app/data/schema.py` is a list of `CREATE ... IF NOT EXISTS` statements with no migrations. New tables appear on the next `ensure_schema`, but column changes never reach an existing database. `stats_compute` keeps its own DDL for its cache tables so it doesn't re-run index creation on `position_results`, so a table it writes to has to be declared in both places.

## Testing

`tests/conftest.py` builds one session-wide database through the real pipeline: season 9999, VER/NOR/LEC over 4 rounds. `tests/unit/test_notable_scenarios.py` documents how its championship ids map to rounds.

Modules bind `get_settings` at import, so patching `app.config` alone isn't enough and fixtures patch each module by name. When a new module imports `get_settings`, add it to the list in `tests/conftest.py`, otherwise it silently reads the real `data/` and `instance/`. `sync_env` in `tests/unit/test_sync_cli.py` and the fixture in `tests/unit/test_rebuild.py` keep lists of their own.

Tests never call Jolpica; `jolpica_service` is patched. The real API allows 4 requests per second, and `THROTTLE_SECONDS` keeps sync under that.

## Repo conventions

- Commit messages follow `type(scope): subject` with types such as `feat`, `fix`, `perf`, `docs`.
- User-visible changes go in `CHANGELOG.md` under `[Unreleased]`.
- `data-sync.yml` pushes `data:` commits straight to `main` on Mondays and Thursdays at 06:00 UTC, so pull before branching.

## Stale material

`CONTRIBUTING.md`, `docs/architecture/`, `docs/setup/`, `.pre-commit-config.yaml` and the docstring in `app/main.py` still describe the removed Flask stack (`flask` commands, black, flake8). Go by `README.md`, `pyproject.toml` and `.github/workflows/ci.yml` instead. The root `championship/` and `graphql_api/` folders are untracked leftovers holding only bytecode.
