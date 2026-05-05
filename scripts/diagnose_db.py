"""One-shot diagnostic: open the production DB, list tables, time each step.

Usage: python scripts/diagnose_db.py
"""
from __future__ import annotations

import sqlite3
import time


def main() -> None:
    t0 = time.time()
    c = sqlite3.connect("instance/championships.db", timeout=10.0)
    print(f"open:    {time.time() - t0:.2f}s")

    t0 = time.time()
    tables = [
        r[0]
        for r in c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
    ]
    print(f"tables:  {tables}")
    print(f"lookup:  {time.time() - t0:.2f}s")

    print(f"jmode:   {c.execute('PRAGMA journal_mode').fetchone()}")
    print(f"h2h?     {'driver_head_to_head' in tables}")
    c.close()


if __name__ == "__main__":
    main()
