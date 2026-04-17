"""Generate every non-empty subset of race indices.

For N races we emit sum_{r=1..N} C(N, r) = 2^N - 1 combinations. A 24-race
season yields 16,777,215 — this is the heavy inner loop of the pipeline.

We stay lazy (generator) so the writer can stream batches straight into SQLite
without materializing the full set in memory.
"""
from __future__ import annotations

import itertools
from typing import Iterator

import numpy as np


def race_combinations(num_races: int) -> Iterator[tuple[int, ...]]:
    """Yield 0-based race-index tuples for every non-empty subset."""
    for r in range(1, num_races + 1):
        yield from itertools.combinations(range(num_races), r)


def total_combinations(num_races: int) -> int:
    """2^N - 1 — the exact row count processed by race_combinations."""
    return (1 << num_races) - 1


def rank_standings(
    drivers: np.ndarray, scores: np.ndarray, race_subset: tuple[int, ...]
) -> tuple[np.ndarray, np.ndarray]:
    """Sum the subset scores and return drivers/scores sorted by descending points."""
    subset_scores = scores[:, list(race_subset)].sum(axis=1)
    order = np.argsort(-subset_scores, kind="stable")
    return drivers[order], subset_scores[order]
