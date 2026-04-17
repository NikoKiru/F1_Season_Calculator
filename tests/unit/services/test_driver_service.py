import pytest

from app.cache import service as cache
from app.services import driver_service


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_get_stats_shape(conn):
    stats = driver_service.get_stats(conn, "VER", 9999)
    expected_keys = {
        "driver_code",
        "driver_name",
        "driver_info",
        "total_wins",
        "total_championships",
        "win_percentage",
        "highest_position",
        "highest_position_championship_id",
        "min_races_to_win",
        "position_distribution",
        "win_probability_by_length",
        "seasons_per_length",
        "head_to_head",
        "season",
    }
    assert expected_keys <= set(stats)
    assert stats["driver_code"] == "VER"
    assert stats["driver_name"] == "Max Verstappen"
    assert stats["total_championships"] == 15


def test_get_stats_totals_consistent(conn):
    totals = 0
    for code in ("VER", "NOR", "LEC"):
        stats = driver_service.get_stats(conn, code, 9999)
        totals += stats["total_wins"]
    assert totals == 15


def test_get_stats_win_percentage_matches(conn):
    stats = driver_service.get_stats(conn, "VER", 9999)
    expected = round((stats["total_wins"] / 15) * 100, 2)
    assert stats["win_percentage"] == expected


def test_get_stats_position_distribution_sums(conn):
    stats = driver_service.get_stats(conn, "LEC", 9999)
    # LEC appears in all 15 championships across 3 possible positions
    total = sum(stats["position_distribution"].values())
    assert total == 15


def test_get_stats_head_to_head_symmetry(conn):
    ver = driver_service.get_stats(conn, "VER", 9999)
    nor = driver_service.get_stats(conn, "NOR", 9999)
    # VER vs NOR wins should mirror NOR vs VER losses
    assert ver["head_to_head"]["NOR"]["wins"] == nor["head_to_head"]["VER"]["losses"]
    assert ver["head_to_head"]["NOR"]["losses"] == nor["head_to_head"]["VER"]["wins"]


def test_head_to_head_preserves_request_order(conn):
    result = driver_service.head_to_head(conn, "VER", "NOR", 9999)
    assert list(result.keys()) == ["VER", "NOR"]
    reversed_ = driver_service.head_to_head(conn, "NOR", "VER", 9999)
    assert list(reversed_.keys()) == ["NOR", "VER"]
    assert result["VER"] == reversed_["VER"]


def test_head_to_head_self_raises(conn):
    with pytest.raises(ValueError):
        driver_service.head_to_head(conn, "VER", "VER", 9999)


def test_position_summary_percentages_sum_to_100(conn):
    summary = driver_service.position_summary(conn, 1, 9999)
    assert summary
    total_pct = sum(row["percentage"] for row in summary)
    # Allow rounding drift
    assert abs(total_pct - 100.0) < 0.1


def test_championships_at_position_pagination(conn):
    result = driver_service.championships_at_position(
        conn, "VER", 1, 9999, page=1, per_page=3
    )
    assert result["driver_code"] == "VER"
    assert result["position"] == 1
    assert result["page"] == 1
    assert result["per_page"] == 3
    assert len(result["championships"]) <= 3
    assert result["total_count"] >= len(result["championships"])
    for c in result["championships"]:
        assert "championship_id" in c
        assert "standings" in c


def test_highest_position_all_has_entry_per_driver(conn):
    rows = driver_service.highest_position_all(conn, 9999)
    codes = {r["driver"] for r in rows}
    assert codes == {"VER", "NOR", "LEC"}
    for r in rows:
        assert 1 <= r["position"] <= 3
