import pytest

from app.cache import service as cache
from app.services import championship_service


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_get_page_first_page_structure(conn):
    page = championship_service.get_page(conn, 9999, page=1, per_page=5)
    assert page["total_results"] == 15
    assert page["total_pages"] == 3
    assert page["current_page"] == 1
    assert page["per_page"] == 5
    assert len(page["results"]) == 5
    assert page["prev_page"] is None
    assert page["next_page"] is not None


def test_get_page_last_page(conn):
    page = championship_service.get_page(conn, 9999, page=3, per_page=5)
    assert page["next_page"] is None
    assert page["current_page"] == 3


def test_championship_results_have_names(conn):
    page = championship_service.get_page(conn, 9999, page=1, per_page=1)
    row = page["results"][0]
    assert "round_names" in row
    assert "driver_points" in row
    assert "driver_names" in row
    assert set(row["driver_points"].keys()) <= {"VER", "NOR", "LEC"}


def test_get_by_id_includes_round_points(conn):
    page = championship_service.get_page(conn, 9999, page=1, per_page=1)
    cid = page["results"][0]["championship_id"]
    detail = championship_service.get_by_id(conn, cid)
    assert detail is not None
    assert "round_points_data" in detail
    for _driver, data in detail["round_points_data"].items():
        assert "round_points" in data
        assert "total_points" in data
        assert sum(data["round_points"]) == data["total_points"]


def test_get_by_id_unknown(conn):
    assert championship_service.get_by_id(conn, 999_999_999) is None


def test_find_by_rounds_roundtrip(conn):
    page = championship_service.get_page(conn, 9999, page=1, per_page=15)
    for result in page["results"]:
        rounds = [int(r) for r in result["rounds"].split(",")]
        cid = championship_service.find_by_rounds(conn, rounds, 9999)
        assert cid == result["championship_id"]


def test_find_by_rounds_missing_returns_none(conn):
    # Rounds 5+ don't exist in our 4-race test season
    assert championship_service.find_by_rounds(conn, [99], 9999) is None


def test_all_wins_totals_equal_championships(conn):
    wins = championship_service.all_wins(conn, 9999)
    assert sum(wins.values()) == 15
    assert set(wins.keys()) <= {"VER", "NOR", "LEC"}


def test_min_races_to_win_for_each_winner(conn):
    wins = championship_service.all_wins(conn, 9999)
    min_races = championship_service.min_races_to_win(conn, 9999)
    assert set(min_races.keys()) == set(wins.keys())
    for _d, n in min_races.items():
        assert 1 <= n <= 4


# --- aggregates come from the precomputed cache ---------------------------
# Counting over championship_results costs a pass over the whole season per
# request: hundreds of milliseconds at 20 rounds, doubling with every round.
# Each test skews win_probability_cache inside this rolled-back transaction
# and expects the skew back, or empties it and expects the live answer.


def _run(conn, sql: str) -> None:
    from sqlalchemy import text

    conn.execute(text(sql))


def test_all_wins_reads_the_precomputed_cache(conn):
    _run(
        conn,
        "UPDATE win_probability_cache SET win_count = 40 "
        "WHERE season = 9999 AND driver_code = 'LEC' AND num_races = 1",
    )
    assert championship_service.all_wins(conn, 9999)["LEC"] == 40


def test_all_wins_falls_back_when_the_cache_is_empty(conn):
    baseline = championship_service.all_wins(conn, 9999)
    cache.clear()
    _run(conn, "DELETE FROM win_probability_cache WHERE season = 9999")
    assert championship_service.all_wins(conn, 9999) == baseline


def test_min_races_to_win_reads_the_precomputed_cache(conn):
    assert championship_service.min_races_to_win(conn, 9999)["VER"] == 1
    cache.clear()
    _run(
        conn,
        "UPDATE win_probability_cache SET win_count = 0 "
        "WHERE season = 9999 AND driver_code = 'VER' AND num_races = 1",
    )
    assert championship_service.min_races_to_win(conn, 9999)["VER"] == 2


def test_min_races_to_win_falls_back_when_the_cache_is_empty(conn):
    baseline = championship_service.min_races_to_win(conn, 9999)
    cache.clear()
    _run(conn, "DELETE FROM win_probability_cache WHERE season = 9999")
    assert championship_service.min_races_to_win(conn, 9999) == baseline


def test_page_total_reads_the_precomputed_cache(conn):
    _run(
        conn,
        "UPDATE win_probability_cache SET total_at_length = 100 "
        "WHERE season = 9999 AND num_races = 4",
    )
    # 4 + 6 + 4 one- to three-round scenarios, plus the skewed full season.
    assert championship_service.get_page(conn, 9999, 1, 1)["total_results"] == 114


def test_page_total_falls_back_when_the_cache_is_empty(conn):
    _run(conn, "DELETE FROM win_probability_cache WHERE season = 9999")
    assert championship_service.get_page(conn, 9999, 1, 1)["total_results"] == 15


def test_scenario_search_is_an_index_lookup(conn):
    """Left to itself the planner filters the whole season by `rounds`: without
    statistics the season index looks as selective as the rounds index."""
    from sqlalchemy import text

    from app.data.queries import championships as q

    plan = conn.execute(
        text("EXPLAIN QUERY PLAN " + q.BY_ROUNDS), {"r": "1,2", "s": 9999}
    ).all()
    assert any("idx_rounds" in row.detail for row in plan), plan
