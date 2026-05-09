# Changelog

All notable user-visible changes to this project. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project
follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
