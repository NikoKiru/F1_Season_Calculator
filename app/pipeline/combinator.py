"""Generate every non-empty subset of race indices.

For N races we emit sum_{r=1..N} C(N, r) = 2^N - 1 combinations. A 24-race
season yields 16,777,215 — this is the heavy inner loop of the pipeline.

We stay lazy (generators) so the writer can stream batches straight into SQLite
without materializing the full set in memory.
"""
from __future__ import annotations

import itertools
from collections.abc import Iterator

import numpy as np

# Race points per finishing position, P10 first. Season CSVs store points, not
# positions, so these ten finishes are all countback can tell apart.
SCORING_RACE_POINTS = np.array([1, 2, 4, 6, 8, 10, 12, 15, 18, 25])


def race_combinations(num_races: int) -> Iterator[tuple[int, ...]]:
    """Yield 0-based race-index tuples for every non-empty subset."""
    for r in range(1, num_races + 1):
        yield from itertools.combinations(range(num_races), r)


def subset_batches(num_races: int, batch_size: int) -> Iterator[np.ndarray]:
    """The subsets of `race_combinations`, in the same order, as index arrays.

    Each array has shape (subsets, length) and holds subsets of one length,
    at most `batch_size` of them, so a batch can be ranked in one go.
    """
    for length in range(1, num_races + 1):
        combos = itertools.combinations(range(num_races), length)
        while True:
            flat = np.fromiter(
                itertools.chain.from_iterable(itertools.islice(combos, batch_size)),
                dtype=np.intp,
            )
            if flat.size == 0:
                break
            yield flat.reshape(-1, length)


def total_combinations(num_races: int) -> int:
    """2^N - 1 — the exact row count processed by race_combinations."""
    return (1 << num_races) - 1


def countback_weights(race_scores: np.ndarray) -> np.ndarray:
    """Per-race weights whose sum over any subset orders entries by countback.

    Countback compares wins, then second places, and so on. Each scoring
    position owns one digit of a base-(races + 1) number, which no count can
    overflow — a position is held at most once per race, even by a team — so
    the digits survive addition across races and teammates.

    Takes race points only: sprint finishes don't count. Points between two
    table values (a fastest-lap bonus) round down to the finish they sit on.
    """
    base = race_scores.shape[1] + 1
    digits = np.concatenate(
        ([0], base ** np.arange(len(SCORING_RACE_POINTS), dtype=np.int64))
    )
    return digits[np.searchsorted(SCORING_RACE_POINTS, race_scores, side="right")]


def rank_standings(
    drivers: np.ndarray,
    scores: np.ndarray,
    race_subset: tuple[int, ...],
    countback: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Sum the subset scores and return drivers/scores sorted by descending points.

    Points ties go to the higher `countback_weights` sum. Entries still level
    keep their array order.
    """
    races = list(race_subset)
    subset_scores = scores[:, races].sum(axis=1)
    subset_countback = countback[:, races].sum(axis=1)
    order = np.lexsort((-subset_countback, -subset_scores))
    return drivers[order], subset_scores[order]


def rank_batch(
    scores: np.ndarray, countback: np.ndarray, subsets: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """`rank_standings` for a whole batch of subsets at once.

    Takes the (subsets, length) index array `subset_batches` yields. Returns
    (order, points), both shaped (subsets, entries): `order[i]` lists entry
    indices from first place down for subset i, and `points[i]` their points
    in that order. The season is 2^N - 1 subsets, so this is the path the
    writers take; one call replaces thousands of `rank_standings` calls.
    """
    selected = np.zeros((subsets.shape[0], scores.shape[1]), dtype=np.int64)
    np.put_along_axis(selected, subsets, 1, axis=1)
    subset_scores = selected @ scores.T
    subset_countback = selected @ countback.T
    # lexsort is stable, so entries level on both keys keep their array order.
    order = np.lexsort((-subset_countback, -subset_scores), axis=1)
    return order, np.take_along_axis(subset_scores, order, axis=1)
