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


def test_subset_batches_follow_race_combinations_order():
    # Championship ids are handed out in this order, so it must not change.
    rows = [
        tuple(row)
        for batch in combinator.subset_batches(5, batch_size=4)
        for row in batch.tolist()
    ]
    assert rows == list(combinator.race_combinations(5))


def test_subset_batches_hold_one_length_and_stay_within_the_batch_size():
    for batch in combinator.subset_batches(6, batch_size=7):
        assert batch.ndim == 2
        assert 1 <= batch.shape[0] <= 7


def test_rank_batch_agrees_with_rank_standings_on_every_subset():
    # Small scores over few entries, so points ties and countback ties both
    # occur and the stable fallback to array order is exercised too.
    rng = np.random.default_rng(7)
    race = rng.choice([*combinator.SCORING_RACE_POINTS.tolist(), 0, 0], size=(6, 7))
    sprint = rng.integers(0, 3, size=(6, 7))
    labels = np.array(["A", "B", "C", "D", "E", "F"], dtype=object)
    scores = race + sprint
    countback = combinator.countback_weights(race)

    seen = 0
    for batch in combinator.subset_batches(7, batch_size=10):
        order, points = combinator.rank_batch(scores, countback, batch)
        for row, subset in enumerate(batch.tolist()):
            want_labels, want_points = combinator.rank_standings(
                labels, scores, tuple(subset), countback
            )
            assert labels[order[row]].tolist() == want_labels.tolist()
            assert points[row].tolist() == want_points.tolist()
            seen += 1
    assert seen == combinator.total_combinations(7)


def test_rank_standings_sorts_descending():
    drivers = np.array(["VER", "NOR", "LEC"])
    scores = np.array([[25, 18, 25, 18], [18, 25, 18, 25], [15, 15, 15, 15]])
    sorted_drivers, sorted_points = combinator.rank_standings(
        drivers, scores, (0, 2), combinator.countback_weights(scores)
    )
    assert sorted_points.tolist() == sorted(sorted_points.tolist(), reverse=True)
    assert sorted_drivers[0] == "VER"


def test_rank_standings_stable_when_countback_is_level():
    # VER and NOR both score 43 over rounds {0,1} with one win and one P2 each,
    # so countback can't split them either — array order stands (stable sort).
    drivers = np.array(["VER", "NOR", "LEC"])
    scores = np.array([[25, 18, 25, 18], [18, 25, 18, 25], [15, 15, 15, 15]])
    sorted_drivers, _ = combinator.rank_standings(
        drivers, scores, (0, 1), combinator.countback_weights(scores)
    )
    assert sorted_drivers[0] == "VER"
    assert sorted_drivers[1] == "NOR"


def _rank_pair(race: list[list[int]], sprint: list[list[int]] | None = None) -> list[str]:
    """Rank VER (row 0) and NOR (row 1) over every round of a season."""
    race_scores = np.array(race)
    season = csv_loader.LoadedSeason(
        drivers=np.array(["VER", "NOR"]),
        round_numbers=np.arange(1, race_scores.shape[1] + 1),
        race_scores=race_scores,
        sprint_scores=np.array(sprint) if sprint else np.zeros_like(race_scores),
    )
    every_round = tuple(range(race_scores.shape[1]))
    ordered, _ = combinator.rank_standings(
        season.drivers, season.combined, every_round, season.countback
    )
    return ordered.tolist()


def test_points_tie_goes_to_the_driver_with_more_wins():
    # 18+18+8 = 25+15+4 = 44. NOR has the only win.
    assert _rank_pair([[18, 18, 8], [25, 15, 4]]) == ["NOR", "VER"]


def test_level_wins_go_to_the_driver_with_more_second_places():
    # 25+12+6 = 25+18+0 = 43. One win each; NOR has the only P2.
    assert _rank_pair([[25, 12, 6], [25, 18, 0]]) == ["NOR", "VER"]


def test_countback_reaches_the_last_scoring_position():
    # 1+1 = 2+0 = 2. A P9 beats any number of P10s.
    assert _rank_pair([[1, 1], [2, 0]]) == ["NOR", "VER"]


def test_one_win_outranks_a_second_place_in_every_race():
    # 18+18 = (25+8)+(0+3) = 36. Two P2s must not roll over into a win.
    assert _rank_pair([[18, 18], [25, 0]], sprint=[[0, 0], [8, 3]]) == ["NOR", "VER"]


def test_sprint_points_do_not_count_as_race_finishes():
    # 18+8 = 25+1 = 26. VER's weekend total looks like a win; only NOR won the race.
    assert _rank_pair([[18], [25]], sprint=[[8], [1]]) == ["NOR", "VER"]


def test_bonus_points_still_count_as_the_finish_they_sit_on():
    # 18+8 = 26+0 = 26. NOR's 26 is a win plus a fastest-lap point.
    assert _rank_pair([[18, 8], [26, 0]]) == ["NOR", "VER"]


def test_csv_loader_basic(tmp_path):
    csv = tmp_path / "c.csv"
    csv.write_text("Driver,1,2,3\nVER,25,18,25\nNOR,18,25,18\n")
    loaded = csv_loader.load(csv)
    assert loaded.drivers.tolist() == ["VER", "NOR"]
    assert loaded.round_numbers.tolist() == [1, 2, 3]
    assert loaded.race_scores.shape == (2, 3)
    assert loaded.race_scores[0].tolist() == [25, 18, 25]
    assert loaded.sprint_scores.sum() == 0
    assert loaded.combined[0].tolist() == [25, 18, 25]


def test_csv_loader_with_sprint_columns(tmp_path):
    csv = tmp_path / "c.csv"
    # Rounds 1, 2 (sprint), 6 (sprint) — round 3/4/5 canceled/skipped
    csv.write_text("Driver,1,2,2s,6,6s\nVER,25,18,8,25,7\nNOR,18,25,6,18,8\n")
    loaded = csv_loader.load(csv)
    assert loaded.round_numbers.tolist() == [1, 2, 6]
    assert loaded.race_scores.tolist() == [[25, 18, 25], [18, 25, 18]]
    assert loaded.sprint_scores.tolist() == [[0, 8, 7], [0, 6, 8]]
    assert loaded.combined.tolist() == [[25, 26, 32], [18, 31, 26]]


def test_csv_loader_sprint_without_matching_race_fails(tmp_path):
    csv = tmp_path / "c.csv"
    csv.write_text("Driver,1,3s\nVER,25,8\n")
    import pytest
    with pytest.raises(csv_loader.CSVLoadError):
        csv_loader.load(csv)
