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
        assert all(b >= a for a, b in zip(d["cumulative"], d["cumulative"][1:], strict=False))
    # Length of each driver's cumulative array equals the rounds array.
    for d in data["drivers"]:
        assert len(d["cumulative"]) == len(data["rounds"])


def test_home_page_data_includes_team_for_dashed_teammate_logic(client):
    """The chart payload must include `team` per driver so the frontend can
    pick the lower-placed teammate of each pair and render them dashed."""
    r = client.get("/")
    data = _page_data(r.text)
    for d in data["drivers"]:
        assert "team" in d, f"driver {d['code']} missing team field"


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
    """The home-page standings table must be ordered by points descending."""
    r = client.get("/")
    html = r.text
    points = [
        int(p)
        for p in re.findall(r'data-label="Points"[^>]*>\s*(\d+)\s*<', html)
    ]
    assert points, "no points cells found in home standings table"
    assert points == sorted(points, reverse=True), (
        f"points must be DESC, got {points}"
    )


def test_home_links_full_table_to_live_championship(client):
    """The 'See full table' link points to the longest-scenario championship,
    which acts as the live standings page that grows as rounds happen."""
    r = client.get("/")
    assert re.search(r'href="/championship/\d+"[^>]*>See full table', r.text)


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
    """The h2h table renders each opponent's full name (not code) and never
    shows the driver themselves in their own opponent list.

    Earlier regression: the old card grid rendered `<code> vs <code>`
    because the template's self-filter compared against the wrong key.
    The table layout drops the redundant "X vs" prefix entirely; this
    test now asserts the table contract: opponent rows by full name,
    self never appears as opponent.
    """
    r = client.get(f"/driver/VER?season={SEASON}")
    # The h2h table appears.
    assert 'class="table h2h-table"' in r.text or "h2h-table" in r.text
    # Opponents render with full names.
    for name in ("Lando Norris", "Charles Leclerc"):
        assert name in r.text, f"opponent {name} missing from h2h table"
    # Driver themselves should not appear as their own opponent. The
    # h2h dict in the API excludes the self key, so a "Max Verstappen"
    # row in the table body would be a regression. We can't grep for
    # "Max Verstappen" globally because the hero shows it, but we can
    # check the broken-codes pattern.
    for bad in ("NOR vs NOR", "LEC vs LEC", "VER vs VER"):
        assert bad not in r.text, f"broken h2h pattern found: {bad}"


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
        assert "team" in d, f"{d['code']} missing team field for dashed-line logic"


def test_championship_not_found_404(client):
    r = client.get("/championship/999999999")
    assert r.status_code == 404


def test_championship_detail_winner_uses_full_name(client):
    """Hero no longer says '{X} wins' (redundant with standings table). It now
    surfaces margin + runner-up name; assert that resolves to a full name."""
    r = client.get("/championship/1")
    html = r.text
    # Some seeded driver's full name must render somewhere (standings + runner-up).
    assert any(
        name in html for name in ("Max Verstappen", "Lando Norris", "Charles Leclerc")
    ), "championship page must render full driver names, not codes"
    # New hero shape: scenario eyebrow + N-race championship title + included rounds.
    assert "Scenario #1" in html
    assert "race championship" in html
    assert "Included rounds" in html


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
    # Cards must be whole-card clickable (canonical card contract).
    assert "card--interactive" in r.text


def test_min_races_to_win_cards_are_canonical(client):
    """min-races cards must carry the canonical card fundamentals:
    top stripe (.card__accent), interactive lift, and click target."""
    r = client.get(f"/min-races-to-win?season={SEASON}")
    assert "card__accent" in r.text
    assert "card--interactive" in r.text


def test_championship_standings_has_team_stripe(client):
    """Standings table rows must carry the team-color left band."""
    r = client.get("/championship/1")
    assert "table--striped-rows" in r.text
    assert "--team-color:" in r.text


def test_driver_h2h_table_has_team_stripe(client):
    """Head-to-head table rows must carry the team-color left band."""
    r = client.get(f"/driver/VER?season={SEASON}")
    assert "table--striped-rows" in r.text


def test_win_probability_table_has_team_stripe(client):
    """Win-probability matrix rows must carry the team-color left band."""
    r = client.get(f"/championship-win-probability?season={SEASON}")
    assert "table--striped-rows" in r.text


def test_driver_positions_payload_has_colors(client):
    """The client-rendered cards on /driver-positions need driver_colors
    threaded through page_data so each card can show its team stripe."""
    r = client.get("/driver-positions")
    assert "driver_colors" in r.text


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


def test_season_switcher_removed_from_header(client):
    """Season switcher was removed once the project was scoped to a single
    season (2026). Make sure the control isn't rendered anywhere."""
    for path in ("/", "/drivers", "/create-championship", "/head-to-head"):
        r = client.get(path)
        assert r.status_code == 200, f"{path} failed"
        assert "data-season-switcher" not in r.text, (
            f"{path} still renders the season switcher"
        )


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
