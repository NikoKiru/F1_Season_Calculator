"""SSR views must not mutate service-cached dicts.

championship_service.get_by_id and statistics_service.win_probability return
the exact object stored in the TTL cache. If a view decorates that object in
place, the /api response for the same resource changes shape depending on
whether the HTML page was rendered first — a heisenbug for API consumers.
"""
from __future__ import annotations

SEASON = 9999

VIEW_ONLY_CHAMPIONSHIP_KEYS = {
    "margin",
    "runner_up_name",
    "winner_color",
    "winner_team",
    "driver_colors",
}


def _first_championship_id(client) -> int:
    r = client.get(f"/api/championships?season={SEASON}&per_page=1")
    assert r.status_code == 200
    return int(r.json()["results"][0]["championship_id"])


def test_championship_api_shape_unaffected_by_page_render(client):
    cid = _first_championship_id(client)

    # Render the HTML page first — this must not poison the cached dict.
    page = client.get(f"/championship/{cid}")
    assert page.status_code == 200

    api = client.get(f"/api/championships/{cid}")
    assert api.status_code == 200
    leaked = VIEW_ONLY_CHAMPIONSHIP_KEYS & set(api.json())
    assert not leaked, f"view-only keys leaked into API response: {sorted(leaked)}"


def test_win_probability_api_shape_unaffected_by_page_render(client):
    page = client.get("/championship-win-probability")
    assert page.status_code == 200

    api = client.get(f"/api/statistics/win-probability?season={SEASON}")
    assert api.status_code == 200
    rows = api.json()["drivers_data"]
    assert rows
    leaked = {"name", "color"} & set(rows[0])
    assert not leaked, f"view-only keys leaked into API rows: {sorted(leaked)}"


def test_constructor_win_probability_cache_unaffected_by_page_render(client, conn):
    """No JSON endpoint exposes constructor win-probability today, but the
    service-cached rows must still come back clean after a page render."""
    from app.services import constructor_service

    page = client.get("/constructor-win-probability")
    assert page.status_code == 200

    rows = constructor_service.win_probability(conn, SEASON)["constructors_data"]
    assert rows
    leaked = {"slug", "color"} & set(rows[0])
    assert not leaked, f"view-only keys leaked into cached rows: {sorted(leaked)}"
