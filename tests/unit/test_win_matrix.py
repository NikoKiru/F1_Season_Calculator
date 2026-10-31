"""The win matrix is a pure view of win counts, so its rules are tested alone."""
from __future__ import annotations

import pytest

from app.services import win_matrix


def _entry(short: str, titles: int, wins: list[int]) -> dict:
    return {
        "name": f"Name {short}",
        "short": short,
        "color": "#123456",
        "href": f"/x/{short}",
        "scenarios_href": f"/x/{short}/position/1",
        "titles": titles,
        "wins": wins,
    }


@pytest.mark.parametrize(
    ("wins", "total", "expected"),
    [
        (0, 48620, "·"),
        (1, 1, "100"),
        (18, 18, "100"),
        (9, 18, "50.0"),
        (2193, 3060, "71.7"),
        (6, 18564, "<0.1"),
        (18558, 18564, ">99.9"),
        (1, 1000, "0.1"),
    ],
)
def test_cell_label(wins, total, expected):
    assert win_matrix.cell_label(wins, total) == expected


def test_shade_is_blank_only_for_true_zero():
    assert win_matrix.shade(0, 48620) == 0
    assert win_matrix.shade(1, 48620) > 0


def test_shade_rises_with_share_and_tops_out_at_100():
    shares = [win_matrix.shade(w, 1000) for w in (1, 50, 200, 500, 999, 1000)]
    assert shares == sorted(shares)
    assert len(set(shares)) == len(shares)
    assert shares[-1] == 100


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (18, "18"),
        (999, "999"),
        (3060, "3.1k"),
        (48620, "48.6k"),
        (134596, "135k"),
        (2704156, "2.7M"),
    ],
)
def test_compact_count(value, expected):
    assert win_matrix.compact_count(value) == expected


def test_build_keeps_winners_and_folds_the_rest():
    matrix = win_matrix.build(
        [_entry("AAA", 3, [1, 2]), _entry("ZZZ", 0, [0, 0]), _entry("MMM", 0, [])],
        [1, 2],
        [2, 2],
    )
    assert [row["short"] for row in matrix["contenders"]] == ["AAA"]
    assert [row["short"] for row in matrix["others"]] == ["MMM", "ZZZ"]


def test_build_cells_carry_exact_counts_behind_the_rounded_label():
    matrix = win_matrix.build([_entry("AAA", 9, [9])], [1], [18])
    cell = matrix["contenders"][0]["cells"][0]
    assert cell == {
        "races": 1,
        "wins": 9,
        "total": 18,
        "label": "50.0",
        "shade": win_matrix.shade(9, 18),
    }


def test_build_totals_the_scenarios_per_length():
    matrix = win_matrix.build([_entry("AAA", 3, [1, 2])], [1, 2], [18, 153])
    assert matrix["scenarios"] == [
        {"races": 1, "total": 18, "label": "18"},
        {"races": 2, "total": 153, "label": "153"},
    ]
    assert matrix["total_scenarios"] == 171


def test_lock_names_the_first_length_of_a_clean_sweep():
    matrix = win_matrix.build(
        [_entry("AAA", 12, [1, 5, 6]), _entry("BBB", 1, [1, 0, 0])],
        [1, 2, 3],
        [2, 5, 6],
    )
    assert matrix["lock"] == {"name": "Name AAA", "from_races": 2}


def test_lock_ignores_a_sweep_of_only_the_full_season():
    """The longest length is a single scenario, so winning it says nothing."""
    matrix = win_matrix.build(
        [_entry("AAA", 2, [1, 1]), _entry("BBB", 1, [1, 0])], [1, 2], [2, 1]
    )
    assert matrix["lock"] is None


def test_no_lock_without_winners():
    assert win_matrix.build([], [], [])["lock"] is None
