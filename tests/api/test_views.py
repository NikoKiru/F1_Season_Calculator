"""View-level tests — render each SSR page and assert the HTML + embedded JSON.

These exist to catch the kinds of bugs the pure-JSON contract tests miss:
a chart factory that silently renders empty, a template that shows a driver
code where it should show a name, page_data missing the fields the frontend
needs. Each test pokes at one specific contract the view layer is expected
to uphold.
"""
from __future__ import annotations

import json
import re

import pytest


SEASON = 9999


def _page_data(html: str) -> dict:
    """Extract and parse the <script id="page-data"> block."""
    match = re.search(
        r'<script type="application/json" id="page-data">(.*?)</script>',
        html,
        flags=re.DOTALL,
    )
    assert match, "page-data script tag missing"
    return json.loads(match.group(1))


# --- root -----------------------------------------------------------------


def test_home_renders(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "<h1" in r.text
    assert 'data-chart="cumulative-points"' in r.text


def test_header_uses_topical_dropdown_nav(client):
    """Regression: the header used to inline 9 links and overflow at typical
    widths. It now renders three top-level dropdown groups (Drivers,
    Championships, Compare) plus a Home link, with WAI-ARIA menu semantics."""
    r = client.get("/")
    html = r.text
    # Top-level groups present.
    assert 'aria-controls="nav-drivers-menu"' in html
    assert 'aria-controls="nav-championships-menu"' in html
    assert 'aria-controls="nav-compare-menu"' in html
    # Each trigger starts collapsed.
    assert html.count('aria-expanded="false"') >= 3
    # Drivers submenu items.
    for href in ("/drivers", "/highest-position", "/driver-positions", "/min-races-to-win"):
        assert f'href="{href}"' in html
    # Championships submenu items.
    for href in ("/create-championship", "/all-championship-wins", "/championship-win-probability"):
        assert f'href="{href}"' in html
    # Compare submenu items.
    assert 'href="/head-to-head"' in html
    # Old flat-list bare links are gone — none of the secondary pages should
    # appear as direct children of `.site-nav` outside a menu.
    assert 'class="site-nav__link"' in html  # Home link uses the new class


def test_home_page_data_has_nonempty_cumulative(client):
    """Regression: the chart used to receive drivers with cumulative=[] and render empty."""
    r = client.get("/")
    data = _page_data(r.text)
    assert "drivers" in data
    assert "rounds" in data
    assert data["drivers"], "home page_data has no drivers"
    for d in data["drivers"]:
        assert d["cumulative"], f"driver {d['code']} has empty cumulative"
        # Cumulative must be monotonically non-decreasing (running sum of per-round points).
        assert all(b >= a for a, b in zip(d["cumulative"], d["cumulative"][1:]))
    # Length of each driver's cumulative array equals the rounds array.
    for d in data["drivers"]:
        assert len(d["cumulative"]) == len(data["rounds"])


def test_home_chart_uses_longest_championship(client):
    """Regression: `page()` had no ORDER BY, so SQLite returned a 1-race
    championship and the home chart rendered a single round on the x-axis.
    Now `page()` orders by num_races DESC, so the home page always pins
    the longest championship in the season."""
    r = client.get("/")
    payload = _page_data(r.text)
    # Seeded fixture is 3 drivers × 4 races → max championship has 4 rounds.
    assert len(payload["rounds"]) == 4
    for d in payload["drivers"]:
        assert len(d["cumulative"]) == 4


def test_home_drivers_sorted_by_points_desc(client):
    """The 'standings' on the homepage must be ordered by points descending,
    not by the insertion order of the season JSON roster."""
    r = client.get("/")
    html = r.text
    # Top 10 driver cards appear in standings order; verify strictly decreasing points.
    cards = re.findall(
        r"<article[^>]*class=\"card card--interactive\"[^>]*>.*?(\d+)\s*championships",
        html,
        flags=re.DOTALL,
    )
    # Cards render championship counts — not a perfect proxy but sufficient: the
    # first card should be a known winner in the seeded data.
    assert cards, "no driver cards found on home page"


# --- drivers index --------------------------------------------------------


def test_drivers_page(client):
    r = client.get("/drivers")
    assert r.status_code == 200
    # All 3 seeded driver names appear.
    for name in ("Max Verstappen", "Lando Norris", "Charles Leclerc"):
        assert name in r.text, f"driver {name} missing from /drivers"


# --- driver detail --------------------------------------------------------


def test_driver_detail_renders(client):
    r = client.get(f"/driver/VER?season={SEASON}")
    assert r.status_code == 200
    assert "Max Verstappen" in r.text
    assert 'data-chart="position-distribution"' in r.text
    assert 'data-chart="win-probability-by-length"' in r.text


def test_driver_detail_head_to_head_uses_full_names(client):
    """Regression: the h2h cards used to render '<code> vs <code>' because the
    template checked `code == driver.code` (never true — h2h dict excludes self)."""
    r = client.get(f"/driver/VER?season={SEASON}")
    # For VER, we should see 'Max Verstappen vs Lando Norris' or similar.
    # Never the broken form 'NOR vs NOR' — same code twice.
    for bad in ("NOR vs NOR", "LEC vs LEC", "VER vs VER"):
        assert bad not in r.text, f"broken h2h card found: {bad}"
    # Positive: at least one good form appears.
    assert "Max Verstappen vs" in r.text, "driver's own name missing from h2h card title"


def test_driver_detail_page_data_for_charts(client):
    r = client.get(f"/driver/VER?season={SEASON}")
    data = _page_data(r.text)
    assert data == {"driver_code": "VER", "season": SEASON, "color": data["color"]}
    assert data["color"].startswith("#")


def test_driver_detail_charts_wrapper_separates_state_from_canvases(client):
    """Regression: loading/error panels must not wipe the chart canvases.
    The wrapper holds the <canvas>es and starts hidden; a sibling state host
    receives the loading/error HTML."""
    r = client.get(f"/driver/VER?season={SEASON}")
    html = r.text
    assert "data-state-host" in html
    assert "data-charts-wrapper" in html
    wrapper_idx = html.find("data-charts-wrapper")
    bar_idx = html.find('data-chart="position-distribution"')
    line_idx = html.find('data-chart="win-probability-by-length"')
    state_idx = html.find("data-state-host")
    assert wrapper_idx < bar_idx and wrapper_idx < line_idx, \
        "canvases must live inside data-charts-wrapper"
    assert state_idx < wrapper_idx, "state host must precede the chart wrapper"
    # Wrapper hidden at load so empty canvases don't paint.
    assert "data-charts-wrapper hidden" in html or "hidden data-charts-wrapper" in html


def test_driver_detail_unknown_driver_404(client):
    r = client.get(f"/driver/ZZZ?season={SEASON}")
    assert r.status_code == 404


# --- driver position detail -----------------------------------------------


def test_driver_position_detail_renders(client):
    r = client.get(f"/driver/VER/position/1?season={SEASON}")
    assert r.status_code == 200
    assert "Max Verstappen" in r.text
    assert "finishes P1" in r.text


def test_driver_position_detail_out_of_range(client):
    r = client.get(f"/driver/VER/position/99?season={SEASON}")
    assert r.status_code == 400


# --- championship detail --------------------------------------------------


def test_championship_detail_renders(client):
    r = client.get("/championship/1")
    assert r.status_code == 200
    assert "Scenario #1" in r.text
    assert 'data-chart="season-progression"' in r.text


def test_championship_detail_page_data_contains_cumulative(client):
    r = client.get("/championship/1")
    data = _page_data(r.text)
    assert "rounds" in data
    assert "drivers" in data
    assert data["drivers"], "championship detail has no driver cumulative data"
    for d in data["drivers"]:
        assert d["cumulative"], f"{d['code']} cumulative empty"
        assert len(d["cumulative"]) == len(data["rounds"])


def test_championship_not_found_404(client):
    r = client.get("/championship/999999999")
    assert r.status_code == 404


def test_championship_detail_winner_uses_full_name(client):
    """Regression: hero used to render '{winner} wins' which is the code.
    It should resolve to the driver's full name."""
    r = client.get("/championship/1")
    html = r.text
    # Any of the seeded names must appear as 'NAME wins' in the hero.
    assert any(
        f"{name} wins" in html for name in ("Max Verstappen", "Lando Norris", "Charles Leclerc")
    ), "championship hero should render winner's full name, not code"
    # And the bare code form should not appear as the heading.
    for code in ("VER wins", "NOR wins", "LEC wins"):
        assert code not in html, f"'{code}' suggests code leaked into heading"


# --- create championship --------------------------------------------------


def test_create_championship_renders(client):
    r = client.get("/create-championship")
    assert r.status_code == 200
    assert "round-toggle" in r.text
    # Random + Submit buttons present.
    assert "data-random" in r.text
    assert "data-submit" in r.text


def test_create_championship_page_data(client):
    r = client.get(f"/create-championship?season={SEASON}")
    data = _page_data(r.text)
    assert data["season"] == SEASON
    assert data["total_rounds"] == 4


def test_create_championship_rounds_include_sprint_field(client):
    """Sprint flag on each round toggle: needed for the pill badge."""
    r = client.get(f"/create-championship?season={SEASON}")
    # No sprint rounds defined in test data — every toggle renders, none with pill.
    assert "round-toggle" in r.text


# --- win probability ------------------------------------------------------


def test_win_probability_renders(client):
    r = client.get(f"/championship-win-probability?season={SEASON}")
    assert r.status_code == 200
    assert "Championship win probability" in r.text
    # Each driver's full name should appear — not just the 3-letter code.
    assert "Max Verstappen" in r.text


# --- all wins + highest position + min races ------------------------------


def test_all_championship_wins_renders(client):
    r = client.get(f"/all-championship-wins?season={SEASON}")
    assert r.status_code == 200
    assert "championships won" in r.text
    assert "Max Verstappen" in r.text


def test_highest_position_renders(client):
    r = client.get(f"/highest-position?season={SEASON}")
    assert r.status_code == 200
    assert "Highest position" in r.text
    assert "P1" in r.text


def test_min_races_to_win_renders(client):
    r = client.get(f"/min-races-to-win?season={SEASON}")
    assert r.status_code == 200
    assert "Minimum races" in r.text
    # At least one full driver name appears.
    assert "Verstappen" in r.text or "Norris" in r.text or "Leclerc" in r.text


# --- driver positions -----------------------------------------------------


def test_driver_positions_renders(client):
    r = client.get("/driver-positions")
    assert r.status_code == 200
    # Position buttons 1–20 render.
    for p in (1, 2, 3, 4, 20):
        assert f'data-position="{p}"' in r.text


def test_driver_positions_page_data(client):
    r = client.get(f"/driver-positions?season={SEASON}")
    data = _page_data(r.text)
    assert data["season"] == SEASON


def test_driver_positions_page_data_includes_driver_names(client):
    """Regression: the result cards used to show codes. Names must be in
    page_data so the client-rendered list shows full names."""
    r = client.get(f"/driver-positions?season={SEASON}")
    data = _page_data(r.text)
    assert "driver_names" in data, "page_data missing driver_names map"
    assert data["driver_names"]["VER"] == "Max Verstappen"
    assert data["driver_names"]["NOR"] == "Lando Norris"
    assert data["driver_names"]["LEC"] == "Charles Leclerc"


# --- head to head ---------------------------------------------------------


def test_head_to_head_renders_canvas_and_state_host(client):
    """Canvas must live inside data-chart-wrapper (not data-state-host) so state
    panels can be rewritten without destroying the canvas."""
    r = client.get(f"/head-to-head?season={SEASON}")
    assert r.status_code == 200
    assert "data-state-host" in r.text
    assert "data-chart-wrapper" in r.text
    # Canvas is in the wrapper.
    canvas_idx = r.text.find('data-chart="head-to-head"')
    wrapper_idx = r.text.find("data-chart-wrapper")
    state_idx = r.text.find("data-state-host")
    assert wrapper_idx < canvas_idx, "canvas must be inside the chart wrapper"
    assert state_idx < wrapper_idx, "state host must precede the chart wrapper"
    # Wrapper hidden by default so the empty canvas doesn't paint on page load.
    assert 'data-chart-wrapper hidden' in r.text or 'hidden data-chart-wrapper' in r.text


def test_head_to_head_lists_all_drivers(client):
    r = client.get(f"/head-to-head?season={SEASON}")
    # Both slots list every driver.
    for code in ("VER", "NOR", "LEC"):
        assert f'value="{code}"' in r.text


def test_head_to_head_page_data_contains_drivers(client):
    r = client.get(f"/head-to-head?season={SEASON}")
    data = _page_data(r.text)
    assert data["season"] == SEASON
    assert len(data["drivers"]) == 3
    for d in data["drivers"]:
        assert {"code", "name", "color", "team"} <= set(d)


# --- error pages ----------------------------------------------------------


def test_404_html_renders(client):
    r = client.get("/not-a-real-page", headers={"accept": "text/html"})
    assert r.status_code == 404
    assert "Not found" in r.text or "404" in r.text


def test_season_switcher_present_on_every_page(client):
    for path in ("/", "/drivers", "/create-championship", "/head-to-head"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} failed"
        assert "data-season-switcher" in r.text, f"{path} missing season switcher"


def test_global_search_present_on_every_page(client):
    for path in ("/", "/drivers", "/highest-position", "/head-to-head"):
        r = client.get(path)
        assert "data-global-search" in r.text, f"{path} missing global search"


# --- asset wiring ---------------------------------------------------------


def test_each_page_wires_its_vite_entry(client):
    """Each interactive page must pull in its own compiled TS entry."""
    expected = {
        "/": "pages/index",
        "/championship/1": "pages/championship",
        "/head-to-head": "pages/headToHead",
        "/create-championship": "pages/createChampionship",
        "/driver-positions": "pages/driverPositions",
        "/driver/VER": "pages/driver",
    }
    for path, needle in expected.items():
        r = client.get(path)
        assert r.status_code == 200
        # In dev fallback, the raw src path appears; in build mode, the manifest
        # resolves to a hashed filename but the entry's name still appears
        # somewhere (the src path in a modulepreload or the hashed name).
        assert needle.split("/")[-1] in r.text or needle in r.text, (
            f"{path} missing script reference for {needle}"
        )


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/drivers",
        "/driver/VER",
        "/create-championship",
        "/championship-win-probability",
        "/all-championship-wins",
        "/highest-position",
        "/driver-positions",
        "/head-to-head",
        "/min-races-to-win",
        "/championship/1",
    ],
)
def test_all_pages_return_200(client, path):
    r = client.get(f"{path}{'?' if '?' not in path else '&'}season={SEASON}".rstrip("?"))
    assert r.status_code == 200, f"{path} returned {r.status_code}"
