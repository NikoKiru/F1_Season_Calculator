# Changelog

All notable user-visible changes to this project. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `f1 sync` — one idempotent command that brings a season fully up to
  date from the Jolpica-F1 API: calendar + sprint flags merged into
  `seasons/{YYYY}.json`, missing race results spliced into the CSV,
  roster stubs for mid-season substitutes, career/palmarès refresh, and
  a full rebuild when new results landed. `--dry-run`, `--no-reprocess`,
  `--bio/--no-bio` flags.
- `f1 new-season` — scaffolds `data/seasons/{YYYY}.json` for a new year
  from the API, carrying over curated fields (team colors, principals,
  championship titles) from the previous season.
- `data-sync.yml` workflow — scheduled twice-weekly GitHub Action that
  runs `f1 sync --no-reprocess` and auto-commits refreshed data files,
  so the repo stays current with zero manual work.
- **Sync** button in the Tkinter manager (`tools/manage_ui.py`) — one
  click replaces the fetch-round-then-build dance.

### Fixed

- `f1 refresh-bio` no longer rewrites `seasons/{YYYY}.json` when nothing
  changed upstream — `updated_at` timestamps only move on real changes,
  killing the noisy no-op git diffs.
- `.env.example` still documented the removed Flask stack; it now lists
  the real pydantic-settings fields.
- `data/README.md`/`README.md` sprint-weekend lists updated to the
  renumbered 2026 calendar (sprints at rounds 2, 4, 5, 9, 12, 16).

- Precomputed `driver_position_distribution` cache table — driver detail
  page now reads position counts via PK lookup instead of scanning
  `position_results` (16M+ rows). Run `f1 compute-stats --season YYYY`
  to populate.
- Per-row "View scenario →" link on the highest-position page. Winners
  link to their biggest-margin scenario; non-winners link to the
  longest scenario at their best finish.
- Compact head-to-head table on the driver detail page with W/L/Win-%
  columns, an inline percentage bar, and a "Compare →" button per row.

### Changed

- Replaced the 22-card head-to-head grid on driver detail with the new
  table — drops the redundant "<DriverName> vs" prefix and sorts by
  win % descending.

## [2.1.0] — 2026-05-09

### Added

- Precomputed `driver_head_to_head` cache table — driver-detail and
  head-to-head pages now respond in <1 s instead of timing out.
- Topical dropdown navigation in the header (Drivers ▾, Championships ▾,
  Compare ▾) with WAI-ARIA menu semantics and keyboard support.
- Loading feedback ("Searching for championship…", "Comparing…") on
  every slow async pane, with retry-able error states.
- Dashed-line rendering for the lower-finishing teammate on cumulative
  points charts; darkened slice for the lower head-to-head winner when
  two teammates share a team color.
- Dark-mode contrast tokens: `--bg-elevated`, `--bg-hover`, `--bg-active`,
  `--fg-on-elevated`. All popovers, dropdowns, selects, and the global
  search input are now legible in both themes.
- Personal Claude skill `optimal-color-contrast` documenting the
  invisible-text patterns and prevention rules.
- `.claude/notes/` covering the 2026 renumber decision, the
  head-to-head schema, the nav keyboard contract, and the missing
  prod index `idx_position_season`.

### Changed

- 2026 season JSON renumbered from "F1-original" gap-numbering to
  sequential 1–22 to match the CSV. Sprint rounds shifted from
  `[2,6,7,11,14,18]` to `[2,4,5,9,12,16]`.
- Home page chart query now `ORDER BY num_races DESC` so the cumulative
  line always spans the longest championship of the season instead of a
  random 1-race scenario.
- API `apiGet` default timeout raised from 5 s to 15 s for cold-cache
  resilience.
- CI workflow rewritten for the FastAPI architecture: ruff lint,
  `pip install -e .[dev]` instead of `requirements.txt`, pytest against
  `tests/unit` + `tests/api`, uvicorn boot validation, and a separate
  Node job that typechecks + builds the Vite bundle.

### Removed

- Legacy Flask app: `app.py`, `__init__.py` (root), `.flaskenv`,
  `championship/` package, top-level `static/` directory,
  `requirements.txt`, and the Flask-era `tests/test_*.py` suite.

### Fixed

- Header dropdown menus rendered white-on-white in dark mode because
  `var(--bg-elevated, #fff)` fell back to white when the token was
  undefined.
- Native `<option>` popups inherited the brand-white text color and
  became unreadable on the system popup background.
- Global search input on the red header had insufficient contrast on
  both background and placeholder.
- Pie chart slices for two teammates rendered as one continuous shape
  because both used the same team color and had no border.

## [2.0.0] — 2026 rewrite

Initial FastAPI + SQLAlchemy Core + Vite/TypeScript rewrite. See git
history for the per-step breakdown — this entry exists to anchor the
versioning baseline.
