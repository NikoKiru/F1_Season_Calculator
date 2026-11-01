# Contributing

## Setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\Activate.ps1    Linux/Mac: source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium
cd web && npm ci && npm run build
```

`web/` needs Node 20.19+ or 22.12+. Start the site with:

```bash
uvicorn "app.main:create_app" --factory --host 127.0.0.1 --port 8000 --reload
```

## Before opening a pull request

Run what CI runs:

```bash
ruff check app tests
pytest tests/unit tests/api --cov=app --cov-fail-under=70
(cd web && npm run typecheck && npm run build)
pytest tests/e2e
```

The e2e tests run against the frontend build, so build first.

Add tests with your change. Tests never call the Jolpica API.

## Conventions

- Commit messages follow `type(scope): subject`, with types such as `feat`, `fix`, `perf` and `docs`.
- User-visible changes go in `CHANGELOG.md` under `[Unreleased]`.
- `data-sync.yml` pushes `data:` commits straight to `main` on Mondays and Thursdays at 06:00 UTC, so run `git pull` before branching and before `f1 sync`.
- Leave the stats in `data/seasons/*.json` to `f1 sync`. Championship titles are the part that's edited by hand.

`CLAUDE.md` covers the architecture and how the pipeline fits together.
