"""Pipeline correctness tests (generator + ranker + CSV loader)."""
from __future__ import annotations

import numpy as np

from app.pipeline import combinator, csv_loader


def test_total_combinations_matches_2_pow_n_minus_1():
    for n in range(1, 11):
        expected = (1 << n) - 1
        assert combinator.total_combinations(n) == expected
        assert sum(1 for _ in combinator.race_combinations(n)) == expected


def test_race_combinations_yields_ordered_tuples():
    combos = list(combinator.race_combinations(3))
    assert combos == [
        (0,), (1,), (2,),
        (0, 1), (0, 2), (1, 2),
        (0, 1, 2),
    ]


def test_rank_standings_sorts_descending():
    drivers = np.array(["VER", "NOR", "LEC"])
    scores = np.array([[25, 18, 25, 18], [18, 25, 18, 25], [15, 15, 15, 15]])
    sorted_drivers, sorted_points = combinator.rank_standings(drivers, scores, (0, 2))
    assert sorted_points.tolist() == sorted(sorted_points.tolist(), reverse=True)
    assert sorted_drivers[0] == "VER"


def test_rank_standings_stable_on_ties():
    # VER and NOR both score 43 over rounds {0,1} — VER should come first (stable sort)
    drivers = np.array(["VER", "NOR", "LEC"])
    scores = np.array([[25, 18, 25, 18], [18, 25, 18, 25], [15, 15, 15, 15]])
    sorted_drivers, _ = combinator.rank_standings(drivers, scores, (0, 1))
    assert sorted_drivers[0] == "VER"
    assert sorted_drivers[1] == "NOR"


def test_csv_loader(tmp_path):
    csv = tmp_path / "c.csv"
    csv.write_text("Driver,1,2,3\nVER,25,18,25\nNOR,18,25,18\n")
    drivers, scores = csv_loader.load(csv)
    assert drivers.tolist() == ["VER", "NOR"]
    assert scores.shape == (2, 3)
    assert scores[0].tolist() == [25, 18, 25]
