# README overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace README.md with a slim showcase + owner reference (design option A).

**Architecture:** Docs-only change on branch `docs/readme-overhaul`, worked in a separate
worktree so the main checkout (running `f1 sync` on `main`, writing `data/` and
`instance/`) is never touched. Screenshots come from the main checkout's server once
the sync has finished.

**Tech Stack:** GitHub-flavoured Markdown, mermaid, PNG screenshots via chrome-devtools MCP.

**Spec:** `docs/superpowers/specs/2026-11-08-readme-overhaul-design.md`

## Global Constraints
- Never run git commands that change the main checkout's working tree or branch while the sync runs.
- Every command, path and flag in the README must exist today (`f1 --help`, `app/config.py`).
- DB path is `instance/championships.db`; frontend install is `npm ci`; Node 20.19+ or 22.12+; Python 3.10+.
- No "mypy strict" badge or claim; no "only the sprints counted" example.
- Target length about 120 lines of Markdown.

## Review Focus
- Relative links (`CONTRIBUTING.md`, `CLAUDE.md`, `data/README.md`, `CHANGELOG.md`, `LICENSE`, `docs/images/*`) all resolve on the branch.
- The centered header `<div align="center">` is closed, so GitHub renders the rest as Markdown.
- Section anchors in the nav row match the rendered heading slugs (emoji headings produce a leading `-`).
- Mermaid block parses on GitHub (no unescaped `|` or parentheses in labels).
- Screenshots are readable at GitHub's ~900px column width and under ~400 KB each.

---

### Task 1: Worktree

- [ ] `git worktree add ../F1_Season_Calculator-readme -b docs/readme-overhaul origin/main`
- [ ] Move the spec and this plan from the main checkout into the worktree's `docs/superpowers/`.
- [ ] Check: `git -C <main checkout> status` shows only the sync's `data/` changes.

### Task 2: Screenshots (after the sync has finished)

**Files:** Create `docs/images/home.png`, `docs/images/championship.png`, `docs/images/notable-scenarios.png` in the worktree.

- [ ] Start uvicorn from the main checkout on port 8001 (read-only use of its DB).
- [ ] Capture `/`, one `/championship/{id}` for the full 2026 season, and the notable-scenarios page at 1280 px wide (mind the DPR quirk in memory).
- [ ] Check: each file opens, shows content (not an error or unstyled page), and is under ~400 KB.
- [ ] Stop the server.

### Task 3: Write README.md

**Files:** Modify `README.md` (full rewrite) in the worktree.

Sections, in order: centered header (title, pitch, badges CI/data sync/Python/license, nav) →
screenshots → why it's interesting (2ⁿ−1, 16,777,215 for 24 rounds, countback) → features
(WDC + WCC, notable scenarios, win probability, head-to-head, auto-sync) → how it works
(one mermaid flowchart) → quick start → day-to-day (sync, dry run, new season, add-race,
fetch-race, Tkinter manager) → CLI table → docs links → license → acknowledgments.

- [ ] Write the file.
- [ ] Check links: every relative target listed in Review Focus exists (`ls`).
- [ ] Check commands: every `f1 <cmd>` appears in `f1 --help`.
- [ ] Check render: `gh api markdown -f mode=gfm -F text=@README.md` returns HTML with an `<h1>` and closed div.

### Task 4: Commit

- [ ] `git add README.md docs/images docs/superpowers && git commit -m "docs(readme): rewrite as showcase with screenshots and current commands"`
- [ ] Ask before pushing / opening a PR.
