import pytest

from app.cache import service as cache
from app.services import constructor_service


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


def test_position_summary_percentages_sum_to_100(conn):
    summary = constructor_service.position_summary(conn, 1, 9999)
    assert summary
    total_pct = sum(row["percentage"] for row in summary)
    assert abs(total_pct - 100.0) < 0.1


def test_position_summary_reads_precomputed_distribution(conn):
    """Same contract as the driver side: read the tiny precomputed
    `constructor_position_distribution` table, not a GROUP BY scan over
    `constructor_position_results`."""
    from sqlalchemy import text

    row = conn.execute(
        text(
            "SELECT constructor_name FROM constructor_position_distribution "
            "WHERE season = 9999 AND position = 1 LIMIT 1"
        )
    ).one()
    conn.execute(
        text(
            "UPDATE constructor_position_distribution SET count = 66 "
            "WHERE season = 9999 AND position = 1 AND constructor_name = :c"
        ),
        {"c": row.constructor_name},
    )
    summary = constructor_service.position_summary(conn, 1, 9999)
    skewed = next(r for r in summary if r["constructor"] == row.constructor_name)
    assert skewed["count"] == 66


def test_position_summary_falls_back_to_live_scan_when_cache_empty(conn):
    from sqlalchemy import text

    baseline = constructor_service.position_summary(conn, 1, 9999)
    cache.clear()
    conn.execute(
        text("DELETE FROM constructor_position_distribution WHERE season = 9999")
    )
    live = constructor_service.position_summary(conn, 1, 9999)
    assert live == baseline


def _position_row(conn, position: int) -> tuple[str, int]:
    from sqlalchemy import text

    row = conn.execute(
        text(
            "SELECT constructor_name, count FROM constructor_position_distribution "
            "WHERE season = 9999 AND position = :p ORDER BY count DESC LIMIT 1"
        ),
        {"p": position},
    ).one()
    return row.constructor_name, int(row.count)


@pytest.mark.parametrize("position", [1, 2])
def test_position_list_runs_longest_scenarios_first(conn, position):
    name, count = _position_row(conn, position)
    result = constructor_service.championships_at_position(
        conn, name, position, 9999, page=1, per_page=500
    )
    rows = result["championships"]
    assert len(rows) == count
    keys = [(r["num_races"], r["championship_id"]) for r in rows]
    assert keys == sorted(keys, reverse=True)


@pytest.mark.parametrize("position", [1, 2])
def test_position_rows_list_their_rounds(conn, position):
    name, _ = _position_row(conn, position)
    rows = constructor_service.championships_at_position(
        conn, name, position, 9999, page=1, per_page=500
    )["championships"]
    assert rows
    for row in rows:
        assert len(row["rounds"]) == row["num_races"]
        assert row["rounds"] == sorted(row["rounds"])
        assert all(isinstance(number, int) for number in row["rounds"])


def test_position_total_reads_precomputed_distribution(conn):
    from sqlalchemy import text

    name, _ = _position_row(conn, 2)
    conn.execute(
        text(
            "UPDATE constructor_position_distribution SET count = 66 "
            "WHERE season = 9999 AND position = 2 AND constructor_name = :c"
        ),
        {"c": name},
    )
    result = constructor_service.championships_at_position(conn, name, 2, 9999, 1, 1)
    assert result["total_count"] == 66


def test_position_total_falls_back_when_distribution_is_empty(conn):
    from sqlalchemy import text

    name, count = _position_row(conn, 2)
    conn.execute(
        text("DELETE FROM constructor_position_distribution WHERE season = 9999")
    )
    live = constructor_service.championships_at_position(conn, name, 2, 9999, 1, 1)
    assert live["total_count"] == count


def test_win_total_reads_precomputed_cache(conn):
    from sqlalchemy import text

    name, _ = _position_row(conn, 1)
    conn.execute(
        text(
            "UPDATE constructor_win_probability_cache SET win_count = 40 "
            "WHERE season = 9999 AND constructor_name = :c AND num_races = 1"
        ),
        {"c": name},
    )
    result = constructor_service.championships_at_position(
        conn, name, 1, 9999, 1, 1, num_races=1
    )
    assert result["total_count"] == 40


def test_win_total_falls_back_when_cache_is_empty(conn):
    from sqlalchemy import text

    name, count = _position_row(conn, 1)
    conn.execute(
        text("DELETE FROM constructor_win_probability_cache WHERE season = 9999")
    )
    live = constructor_service.championships_at_position(conn, name, 1, 9999, 1, 1)
    assert live["total_count"] == count


def test_wins_can_be_narrowed_to_one_season_length(conn):
    name, _ = _position_row(conn, 1)
    everything = constructor_service.championships_at_position(
        conn, name, 1, 9999, 1, 500
    )
    expected = [c for c in everything["championships"] if c["num_races"] == 1]
    assert 0 < len(expected) < len(everything["championships"])

    narrowed = constructor_service.championships_at_position(
        conn, name, 1, 9999, 1, 500, num_races=1
    )
    assert narrowed["championships"] == expected
    assert narrowed["total_count"] == len(expected)
    assert narrowed["num_races"] == 1
