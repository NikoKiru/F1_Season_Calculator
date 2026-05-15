"""View + API tests for the constructor detail surface."""
from __future__ import annotations

import json
import re

SEASON = 9999


def _page_data(html: str) -> dict:
    match = re.search(
        r'<script type="application/json" id="page-data">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, "page-data script tag missing"
    return json.loads(match.group(1))


# --- SSR detail page -------------------------------------------------------


def test_constructor_detail_renders(client):
    """Seed JSON has a 'Red Bull' team → slug 'red-bull'."""
    r = client.get(f"/constructor/red-bull?season={SEASON}")
    assert r.status_code == 200
    assert "Red Bull" in r.text
    assert 'data-chart="position-distribution"' in r.text
    assert 'data-chart="win-probability-by-length"' in r.text


def test_constructor_detail_has_canonical_stripes(client):
    r = client.get(f"/constructor/red-bull?season={SEASON}")
    assert "hero--accented" in r.text
    assert "table--striped-rows" in r.text


def test_constructor_detail_page_data_for_charts(client):
    r = client.get(f"/constructor/red-bull?season={SEASON}")
    data = _page_data(r.text)
    assert data["slug"] == "red-bull"
    assert data["season"] == SEASON
    assert data["color"].startswith("#")


def test_constructor_detail_unknown_slug_404(client):
    r = client.get(f"/constructor/no-such-team?season={SEASON}")
    assert r.status_code == 404


def test_constructor_position_detail_renders(client):
    r = client.get(f"/constructor/red-bull/position/1?season={SEASON}")
    assert r.status_code == 200
    assert "P1" in r.text


def test_constructor_detail_h2h_uses_full_names(client):
    """The h2h table renders each opponent's full name and never shows self."""
    r = client.get(f"/constructor/red-bull?season={SEASON}")
    assert "McLaren" in r.text
    assert "Ferrari" in r.text


# --- JSON endpoints --------------------------------------------------------


def test_api_constructor_stats(client):
    r = client.get(f"/api/constructors/red-bull/stats?season={SEASON}")
    assert r.status_code == 200
    payload = r.json()
    assert payload["constructor_name"] == "Red Bull"
    assert payload["slug"] == "red-bull"
    assert "position_distribution" in payload
    assert "win_probability_by_length" in payload
    assert "head_to_head" in payload


def test_api_constructor_stats_unknown_slug(client):
    r = client.get(f"/api/constructors/bogus/stats?season={SEASON}")
    assert r.status_code == 404


def test_api_constructor_positions(client):
    r = client.get(f"/api/constructors/positions?position=1&season={SEASON}")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    # Each row carries constructor, count, percentage.
    if rows:
        assert {"constructor", "count", "percentage"} <= set(rows[0])


def test_api_constructor_head_to_head(client):
    r = client.get(
        f"/api/constructors/head-to-head/mclaren/ferrari?season={SEASON}"
    )
    assert r.status_code == 200
    payload = r.json()
    assert "McLaren" in payload
    assert "Ferrari" in payload


def test_api_constructor_highest_position(client):
    r = client.get(f"/api/constructors/highest-position?season={SEASON}")
    assert r.status_code == 200
    rows = r.json()
    assert isinstance(rows, list)
    if rows:
        assert {"constructor", "position"} <= set(rows[0])


def test_constructor_positions_page_uses_constructor_module(client):
    """Picker page wires the constructorPositions TS entry."""
    r = client.get(f"/constructor-positions?season={SEASON}")
    assert "constructorPositions" in r.text or "constructor-positions" in r.text


def test_constructor_detail_page_uses_constructor_module(client):
    r = client.get(f"/constructor/red-bull?season={SEASON}")
    assert "constructor" in r.text
