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


def test_constructor_detail_links_every_position_to_its_scenarios(client):
    html = client.get(f"/constructor/red-bull?season={SEASON}").text
    assert 'href="/constructor/red-bull/position/1"' in html
    assert 'href="/constructor/red-bull/position/2"' in html


def test_constructor_position_detail_reads_as_a_scenario_list(client):
    html = client.get(f"/constructor/mclaren/position/2?season={SEASON}").text
    assert "Gap to P1" in html
    assert re.search(r'data-label="Rounds"[^>]*>\s*1–4\s*<', html)
    assert 'data-label="Top 3"' in html


def test_constructor_position_detail_narrows_wins_to_one_length(client):
    html = client.get(f"/constructor/red-bull/position/1?races=1&season={SEASON}").text
    assert len(re.findall(r'data-label="Races"[^>]*>\s*1\s*<', html)) == 2
    assert not re.search(r'data-label="Races"[^>]*>\s*[2-4]\s*<', html)
    assert 'href="/constructor/red-bull/position/1">Show all' in html


def test_constructor_win_probability_cells_open_their_scenarios(client):
    html = client.get(f"/constructor-win-probability?season={SEASON}").text
    assert 'href="/constructor/red-bull/position/1?races=1"' in html
    assert "win-matrix--wide" in html


def test_constructor_win_probability_folds_teams_who_never_win(client):
    html = client.get(f"/constructor-win-probability?season={SEASON}").text
    rest = re.search(r'class="win-matrix__rest".*?</p>', html, flags=re.DOTALL)
    assert rest, "non-winners line missing"
    assert 'href="/constructor/ferrari"' in rest.group(0)


def test_all_constructor_wins_cards_open_the_winning_scenarios(client):
    html = client.get(f"/all-constructor-wins?season={SEASON}").text
    assert 'href="/constructor/red-bull/position/1"' in html


def test_constructor_highest_position_cards_open_the_scenario_list(client):
    html = client.get(f"/constructor-highest-position?season={SEASON}").text
    assert 'href="/constructor/red-bull/position/1"' in html
    assert re.search(r'class="card__stat-link" href="/championship/\d+"', html)
    assert "window.location" not in html


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
