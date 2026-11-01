"""End-to-end smoke coverage for every SSR page."""
from __future__ import annotations

import re

import pytest

PAGES = [
    "/",
    "/drivers",
    "/driver/VER",
    "/driver/VER/position/1",
    "/create-championship",
    "/championship-win-probability",
    "/constructor-win-probability",
    "/all-championship-wins",
    "/highest-position",
    "/driver-positions",
    "/head-to-head",
    "/min-races-to-win",
    "/championship/1",
]


@pytest.mark.parametrize("path", PAGES)
def test_page_renders(live_server, page, path):
    page.goto(f"{live_server}{path}")
    # Every page shares the site header.
    page.wait_for_selector(".site-header")
    # Hero or section heading is mandatory.
    assert page.locator("h1").first.is_visible()


def test_home_has_chart_canvas(live_server, page):
    page.goto(f"{live_server}/")
    assert page.locator('canvas[data-chart="cumulative-points"]').count() == 1


def test_driver_detail_loads_stats(live_server, page):
    page.goto(f"{live_server}/driver/VER")
    page.wait_for_selector(".stat-tile")
    assert page.locator(".stat-tile").count() >= 1


def _wait_for_chart(page, selector: str) -> None:
    """Chart.js sizes the canvas through its style attribute once it has drawn."""
    page.wait_for_function(
        "selector => document.querySelector(selector)?.style.width",
        arg=selector,
    )


@pytest.mark.parametrize(
    ("path", "url"),
    [
        ("/driver/VER", r"/driver/VER/position/\d+$"),
        ("/constructor/red-bull", r"/constructor/red-bull/position/\d+$"),
    ],
)
def test_position_chart_bars_open_their_scenarios(live_server, page, path, url):
    page.goto(f"{live_server}{path}")
    selector = 'canvas[data-chart="position-distribution"]'
    _wait_for_chart(page, selector)
    chart = page.locator(selector)
    box = chart.bounding_box()
    # Clicking the locator scrolls it into view first: the chart sits below the fold.
    chart.click(position={"x": box["width"] * 0.3, "y": box["height"] * 0.5})
    page.wait_for_url(re.compile(url))
    assert "scenarios where" in page.locator("h1").inner_text().lower()


@pytest.mark.parametrize(
    ("path", "url"),
    [
        ("/driver-positions", r"/driver/\w+/position/2$"),
        ("/constructor-positions", r"/constructor/[\w-]+/position/2$"),
    ],
)
def test_position_finishers_open_their_scenarios(live_server, page, path, url):
    page.goto(f"{live_server}{path}")
    page.locator('[data-position="2"]').click()
    page.locator("[data-position-results] .card__title a").first.click()
    page.wait_for_url(re.compile(url))


def test_win_matrix_tile_opens_that_season_length(live_server, page):
    page.goto(f"{live_server}/championship-win-probability")
    page.locator(".win-matrix-frame--wide .win-matrix__tile a").first.click()
    page.wait_for_url(re.compile(r"/driver/\w+/position/1\?races=\d+$"))


@pytest.mark.parametrize(
    ("width", "shown", "hidden"),
    [(1440, "wide", "tall"), (1200, "wide", "tall"), (1024, "tall", "wide"), (390, "tall", "wide")],
)
@pytest.mark.parametrize("path", ["/championship-win-probability", "/constructor-win-probability"])
def test_win_matrix_fits_without_sideways_scrolling(live_server, page, path, width, shown, hidden):
    page.set_viewport_size({"width": width, "height": 844})
    page.goto(f"{live_server}{path}")
    frame = page.locator(f".win-matrix-frame--{shown}")
    assert frame.is_visible()
    assert page.locator(f".win-matrix-frame--{hidden}").is_hidden()
    assert frame.evaluate("el => el.scrollWidth <= el.clientWidth")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")


def test_highest_position_stat_opens_the_best_scenario(live_server, page):
    page.goto(f"{live_server}/highest-position")
    page.locator(".card__stat-link").first.click()
    page.wait_for_url(re.compile(r"/championship/\d+$"))


def test_skip_link_is_first_focusable(live_server, page):
    page.goto(f"{live_server}/")
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement?.className")
    assert "skip-to-content" in (focused or "")
