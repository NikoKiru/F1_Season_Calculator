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


POSITION_PAGES = ["/driver-positions", "/constructor-positions"]


@pytest.mark.parametrize("path", POSITION_PAGES)
def test_position_deep_link_opens_that_position(live_server, page, path):
    page.goto(f"{live_server}{path}?p=2")
    assert page.locator('[data-position="2"]').get_attribute("aria-pressed") == "true"
    page.wait_for_selector("[data-position-results] .section__title")
    assert "P2 finishers" in page.locator("[data-position-results]").text_content()


@pytest.mark.parametrize("path", POSITION_PAGES)
def test_choosing_a_position_updates_the_url(live_server, page, path):
    page.goto(f"{live_server}{path}")
    page.locator('[data-position="1"]').click()
    page.wait_for_url(re.compile(r"\?p=1$"))


@pytest.mark.parametrize("path", POSITION_PAGES)
def test_choosing_a_position_keeps_the_season_in_the_url(live_server, page, path):
    page.goto(f"{live_server}{path}?season=9999")
    page.locator('[data-position="1"]').click()
    page.wait_for_url(re.compile(r"p=1"))
    assert "season=9999" in page.url


@pytest.mark.parametrize(
    ("path", "url"),
    [
        ("/driver-positions", r"/driver/\w+$"),
        ("/constructor-positions", r"/constructor/[\w-]+$"),
    ],
)
def test_position_cards_link_to_the_profile(live_server, page, path, url):
    page.goto(f"{live_server}{path}?p=2")
    page.locator("[data-position-results] .card__meta a").first.click()
    page.wait_for_url(re.compile(url))


def test_copy_link_copies_the_address_with_its_query(live_server, page):
    page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    page.goto(f"{live_server}/driver-positions?p=2")
    button = page.locator("[data-copy-link]")
    button.click()
    page.wait_for_selector('[data-copy-link][data-state="copied"]')
    assert page.evaluate("navigator.clipboard.readText()") == page.url
    assert button.get_attribute("aria-label") == "Link copied"
    assert page.locator("[data-copy-link-status]").text_content() == "Link copied"


def test_copy_link_says_so_when_the_clipboard_is_unavailable(live_server, page):
    page.goto(f"{live_server}/")
    page.evaluate(
        "Object.defineProperty(navigator, 'clipboard', {value: undefined, configurable: true})"
    )
    page.locator("[data-copy-link]").click()
    page.wait_for_selector('[data-copy-link][data-state="failed"]')
    assert page.locator("[data-copy-link]").get_attribute("aria-label") == "Couldn't copy the link"


@pytest.mark.parametrize("width", [320, 344, 360, 390, 768, 1101, 1280])
def test_header_controls_fit_on_screen(live_server, page, width):
    page.set_viewport_size({"width": width, "height": 800})
    page.goto(f"{live_server}/")
    for control in ("[data-copy-link]", "[data-theme-toggle]"):
        box = page.locator(control).bounding_box()
        assert box is not None
        assert box["x"] >= 0
        assert box["x"] + box["width"] <= width
    if width <= 1100:
        assert page.locator("[data-hamburger]").bounding_box()["width"] == 40
    assert page.locator(".brand-text").is_visible() == (width >= 360)
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
