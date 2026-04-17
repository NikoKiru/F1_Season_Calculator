import pytest

from app.cache import service as cache
from app.services import statistics_service


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_win_probability_structure(conn):
    result = statistics_service.win_probability(conn, 9999)
    assert result["season"] == 9999
    assert result["season_lengths"] == [1, 2, 3, 4]
    # C(4,1)=4, C(4,2)=6, C(4,3)=4, C(4,4)=1
    assert result["possible_seasons"] == [4, 6, 4, 1]
    assert result["drivers_data"]


def test_win_probability_rows_shape(conn):
    result = statistics_service.win_probability(conn, 9999)
    for row in result["drivers_data"]:
        assert "driver" in row
        assert "total_titles" in row
        assert len(row["wins_per_length"]) == len(result["season_lengths"])
        assert len(row["percentages"]) == len(result["season_lengths"])
        for wins, total in zip(row["wins_per_length"], result["possible_seasons"]):
            assert 0 <= wins <= total


def test_win_probability_totals_match_possible(conn):
    result = statistics_service.win_probability(conn, 9999)
    column_sums = [0] * len(result["season_lengths"])
    for row in result["drivers_data"]:
        for i, w in enumerate(row["wins_per_length"]):
            column_sums[i] += w
    assert column_sums == result["possible_seasons"]
