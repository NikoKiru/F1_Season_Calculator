"""End-to-end smoke coverage for every SSR page."""
from __future__ import annotations

import pytest


PAGES = [
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


def test_skip_link_is_first_focusable(live_server, page):
    page.goto(f"{live_server}/")
    page.keyboard.press("Tab")
    focused = page.evaluate("document.activeElement?.className")
    assert "skip-to-content" in (focused or "")
