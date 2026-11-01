"""Shape win counts into the matrix both win-probability pages draw.

The percentages in `win_probability` are rounded for the API, so a real but
tiny share and a true zero look alike there. Everything here works from the
exact counts instead, which is also what lets `·` mean "never" and nothing else.

The whole grid has to fit on one screen, which is why labels are short. The
exact figures stay in each cell's tooltip and on the page it links to.
"""
from __future__ import annotations

from math import sqrt
from typing import Any

ZERO_LABEL = "·"


def cell_label(wins: int, total: int) -> str:
    if wins == 0:
        return ZERO_LABEL
    if wins == total:
        return "100"
    pct = wins / total * 100
    if pct < 0.1:
        return "<0.1"
    if pct > 99.9:
        return ">99.9"
    return f"{pct:.1f}"


def shade(wins: int, total: int) -> int:
    """Tile strength from 0 to 100.

    A square-root scale keeps a 0.4% share visible beside a 90% one. 100 is
    reserved for a clean sweep and 0 for never.
    """
    if wins == 0:
        return 0
    if wins == total:
        return 100
    return min(99, max(1, round(sqrt(wins / total) * 100)))


def compact_count(value: int) -> str:
    if value < 1_000:
        return str(value)
    if value < 100_000:
        return f"{value / 1_000:.1f}k"
    if value < 999_500:
        return f"{round(value / 1_000)}k"
    return f"{value / 1_000_000:.1f}M"


def _lock(contenders: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Who wins every scenario from some season length up to the full season.

    A sweep of only the longest length is skipped: that length is a single
    scenario, so it just restates the real standings.
    """
    for row in contenders:
        cells = row["cells"]
        start = len(cells)
        while start > 0 and cells[start - 1]["wins"] == cells[start - 1]["total"]:
            start -= 1
        if len(cells) - start >= 2:
            return {"name": row["name"], "from_races": cells[start]["races"]}
    return None


def build(
    entries: list[dict[str, Any]], lengths: list[int], possible: list[int]
) -> dict[str, Any]:
    """Split entries into title winners with cells, and everyone else.

    Each entry holds `name`, `short`, `color`, `href`, `scenarios_href`,
    `titles` and `wins`, with `wins` aligned to `lengths`.
    """
    contenders = [
        {
            **entry,
            "titles_label": compact_count(entry["titles"]),
            "cells": [
                {
                    "races": races,
                    "wins": wins,
                    "total": total,
                    "label": cell_label(wins, total),
                    "shade": shade(wins, total),
                }
                for races, wins, total in zip(lengths, entry["wins"], possible, strict=True)
            ],
        }
        for entry in entries
        if entry["titles"] > 0
    ]
    return {
        "scenarios": [
            {"races": races, "total": total, "label": compact_count(total)}
            for races, total in zip(lengths, possible, strict=True)
        ],
        "total_scenarios": sum(possible),
        "total_label": compact_count(sum(possible)),
        "contenders": contenders,
        "others": sorted(
            (entry for entry in entries if entry["titles"] == 0),
            key=lambda entry: entry["short"],
        ),
        "lock": _lock(contenders),
    }
