# F1 Season Calculator

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.110+-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

> Explore every "what-if" championship scenario for a Formula 1 season.
> Given per-race points for a season, the calculator enumerates all
> non-empty subsets of rounds (up to 16,777,215 for a 24-race year) and
> tells you who wins, by how much, and on which round.

## What's inside

- **FastAPI + SQLAlchemy Core + SQLite** backend with OpenAPI docs at
  `/api/docs`
- **Jinja2 SSR + Vite + TypeScript** frontend — multi-entry bundles,
  Chart.js loaded only on pages that need it
- **Typer CLI** (`f1 …`) for data ingest, incremental updates, and
  fetching results from the [Jolpica-F1](https://jolpi.ca) API
- **Sprint-aware data model** — sprint points are stored in dedicated
  `{N}s` columns and surfaced separately in the UI
- Unit, API-contract, and (optional) Playwright e2e test suites

## Prerequisites

- **Python 3.10+** (tested on 3.10 – 3.13)
- **Node.js 18+** (ships with `npm`) — for building the Vite frontend.
  Get it from [nodejs.org](https://nodejs.org/). `pnpm` and `yarn` also
  work with the `package.json` scripts if you prefer them.

## Quick start

```bash
# 1. Clone and install (editable)
git clone https://github.com/NikoKiru/F1_Season_Calculator.git
cd F1_Season_Calculator
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1    Linux/Mac: source .venv/bin/activate
pip install -e .

# 2. Scaffold folders + empty DB + sample CSV
f1 setup

# 3. Point it at a season (2026 ships with starter data)
f1 process-data --season 2026
f1 compute-stats --season 2026

# 4. Build frontend assets (once; use `npm run dev` for watch mode)
cd web
npm install
npm run build
cd ..

# 5. Serve
uvicorn "app.main:create_app" --factory --host 127.0.0.1 --port 8000 --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). API docs are at
`/api/docs`.

## Data pipeline

```
data/championships_{YYYY}.csv   ──┐
data/seasons/{YYYY}.json        ──┼─▶  f1 process-data  ──▶  instance/f1.db
                                  │     (combinator + writer)
                                  └─▶  f1 compute-stats ──▶  stats tables
```

The CSV is the single source of truth for points. See
[`data/README.md`](data/README.md) for the exact format including
**sprint columns** (`{N}s`) and the 2026 calendar.

### Keeping a live season current

```bash
# Manual entry (optional --sprint on sprint weekends)
f1 add-race --season 2026 --race 3 \
  --results "VER:25,NOR:18,LEC:15,PIA:12" \
  --sprint  "VER:8,NOR:7,LEC:6"

# Or pull from Jolpica-F1 (Ergast-compatible API)
f1 fetch-race --season 2026 --round 3
```

Both commands rewrite the season CSV and reprocess the season. Use
`--no-reprocess` when batching multiple rounds and reprocess once at the
end.

## 2026 calendar notes

- **Canceled:** Round 4 (Bahrain), Round 5 (Saudi Arabia)
- **Sprint weekends:** Rounds 2 (China), 6 (Miami), 7 (Canada),
  11 (Silverstone), 14 (Zandvoort), 18 (Singapore)

The app respects the real round numbering — canceled rounds are absent
from the CSV header, not padded with zeros.

## CLI

| Command | Description |
| --- | --- |
| `f1 setup` | Create `data/`, `instance/`, sample CSV, empty DB |
| `f1 process-data --season YYYY` | Generate all championships from CSV |
| `f1 compute-stats --season YYYY` | Pre-compute driver statistics + win probability cache |
| `f1 add-race --season YYYY --race N --results "…" [--sprint "…"]` | Append a weekend's results |
| `f1 fetch-race --season YYYY --round N [--no-reprocess]` | Pull race + sprint from Jolpica and splice in |

> The `f1` script is registered by `pip install -e .`. If your shell
> can't find it after install, reopen the terminal so the new `Scripts/`
> entry is on `PATH`, or invoke the CLI directly with
> `python -m app.cli …` — it runs the exact same Typer app.

## HTTP API

The REST surface lives under `/api/*` — full schema at `/api/openapi.json`
and interactive docs at `/api/docs`. Highlights:

| Endpoint | Purpose |
| --- | --- |
| `GET /api/championships` | Paginated championship list |
| `GET /api/championships/{id}` | Full championship detail incl. per-round race/sprint points |
| `GET /api/championships/wins` | Wins per driver |
| `GET /api/championships/min-races-to-win` | Fewest rounds needed to win per driver |
| `GET /api/drivers/{code}/stats` | Consolidated driver stats (one query) |
| `GET /api/drivers/{code}/position/{n}` | Paginated scenarios where driver finished Pn |
| `GET /api/drivers/head-to-head/{a}/{b}` | Win/loss split between two drivers |
| `GET /api/drivers/highest-position` | Each driver's best-ever finish |
| `GET /api/drivers/positions?position=N` | Share of scenarios per driver at position N |
| `GET /api/statistics/win-probability` | Win probability by season length |
| `GET /api/search/championship?rounds=1,2,3` | Look up a championship by rounds |

## Project layout

```
app/                     FastAPI backend
├── main.py              App factory
├── api/                 HTTP routers (thin, delegate to services)
├── views/               SSR page controllers
├── services/            Business logic — championship, driver, stats, jolpica
├── domain/              Pydantic models
├── data/                SQLAlchemy engine + raw SQL
├── pipeline/            CSV loader, combinator, writer, stats compute
├── cli/                 Typer commands (setup, process-data, add-race, fetch-race, …)
├── cache/               In-memory cache service
└── templates/           Jinja2 templates (SSR)

web/                     Frontend source
├── src/pages/           One TS entry per interactive page
├── src/components/      Shared chart factories, slot picker, state panels
├── src/styles/          Design tokens + component CSS
└── vite.config.ts       Multi-entry build → app/static/dist/

data/                    Your CSV + season JSON (user data)
instance/                SQLite file
tests/                   unit/ + api/ + e2e/
```

## Frontend development

The `web/` directory is a standard Vite + TypeScript project. From inside it:

| Command | What it does |
| --- | --- |
| `npm install` | Install frontend dependencies |
| `npm run build` | One-off production build → `app/static/dist/` |
| `npm run dev` | Vite dev server with HMR (run alongside `uvicorn --reload`) |
| `npm run typecheck` | `tsc --noEmit` |

FastAPI reads `app/static/dist/manifest.json` at startup to resolve hashed
asset URLs, so rebuild after changing any TS/CSS file (or leave `npm run
dev` running).

## Tests

```bash
pytest                           # unit + API contract (~2s)
pytest tests/e2e                 # Playwright (auto-skips if not installed)
```

Coverage is checked in CI; unit tests use a seeded in-memory SQLite DB
built by the real pipeline, so they exercise CSV loader → combinator →
writer → services end-to-end.

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

- [Jolpica-F1](https://jolpi.ca) — the Ergast successor API this project
  uses for race results.
- [ChainBear](https://www.youtube.com/@ChainBear) for the original
  "what if only these races counted?" F1 analysis format.
