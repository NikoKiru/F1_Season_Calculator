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
