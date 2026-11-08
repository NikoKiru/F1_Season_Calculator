# README overhaul — design

## Intent
The README serves two readers: the owner (finding the commands months later) and
visitors the owner wants to impress. It has to hook a visitor in the first screen
and give the owner a short, correct working reference below that.

## Goals
- Restore a real header (title, one-line pitch, badges, nav links), which was lost in 9fd3c75
  and leaves an unclosed `<div align="center">` at the top.
- Show the site: 2–3 screenshots of the running local site, stored in `docs/images/`.
- Cover both WDC and WCC, Notable Scenarios and the twice-weekly auto-sync.
- Correct every stale fact: `instance/championships.db`, `f1 sync` as the one
  command, `npm ci`, no "mypy strict" claim, no "only the sprints" example
  (subsets pick whole weekends).
- Owner workflow: pull → `f1 sync` → rebuild frontend → restart, new season, dry run.

## Non-goals
- Architecture deep-dive, CI command list, test internals, full API table: link to
  `CONTRIBUTING.md`, `CLAUDE.md`, `data/README.md` and `/api/docs` instead.
- Changing CONTRIBUTING.md or CLAUDE.md.

## Anti-goals
- A README that claims things the code doesn't do.
- Duplicating material that already lives in the linked files.

## Approaches
- **A. Slim showcase + links (picked).** Hook and screenshots up top, features, one
  diagram, 5-line quick start, owner workflow, links out. About 120 lines.
- B. Everything in one file, repaired. Complete but long, duplicates, drifts again.
- C. Like A with diagrams instead of screenshots. Less work, less showing off.

## Shape
1. Centered header: title, pitch, badges (CI, data sync, Python, license), nav.
2. Screenshots (home/win probability, a championship, notable scenarios).
3. "Why it's interesting": 2ⁿ−1 subsets, 16,777,215 for a 24-round year, countback.
4. Features (short bullets).
5. How it works: one mermaid flowchart CSV+JSON → rebuild → SQLite → FastAPI/Vite.
6. Quick start.
7. Day-to-day: sync, dry run, new season, manual race entry, Tkinter manager.
8. CLI table (current commands, incl. constructor ones).
9. Docs/links, license, acknowledgments.

## Left to the builder
Wording, emoji use, which exact pages to screenshot, badge styling.
