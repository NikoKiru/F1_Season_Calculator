"""Small text formatters shared by the templates."""
from __future__ import annotations


def round_ranges(rounds: list[int]) -> str:
    """Collapse sorted round numbers, so a long scenario stays one short line."""
    spans: list[list[int]] = []
    for number in rounds:
        if spans and number == spans[-1][1] + 1:
            spans[-1][1] = number
        else:
            spans.append([number, number])
    return ", ".join(
        str(first) if first == last else f"{first}–{last}" for first, last in spans
    )
