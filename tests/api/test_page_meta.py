"""Every page describes itself, so a shared link says what it points at."""
from __future__ import annotations

import html as html_lib
import re

import pytest

SEASON = "9999"
DEFAULT_DESCRIPTION = "Explore every possible F1 championship outcome for the season."

# Path -> text its description must contain.
PAGES = {
    "/": SEASON,
    "/drivers": SEASON,
    "/driver/VER": "Max Verstappen",
    "/driver/VER/position/1": "Max Verstappen",
    "/championship/1": "F1 championship",
    "/create-championship": SEASON,
    "/championship-win-probability": SEASON,
    "/all-championship-wins": SEASON,
    "/highest-position": SEASON,
    "/driver-positions": SEASON,
    "/head-to-head": SEASON,
    "/min-races-to-win": SEASON,
    "/notable-scenarios": SEASON,
    "/constructors": SEASON,
    "/constructor/red-bull": "Red Bull",
    "/constructor/red-bull/position/1": "Red Bull",
    "/all-constructor-wins": SEASON,
    "/constructor-win-probability": SEASON,
    "/constructor-min-races-to-win": SEASON,
    "/constructor-highest-position": SEASON,
    "/constructor-positions": SEASON,
}


def _meta(html: str, attribute: str, name: str) -> str | None:
    match = re.search(rf'<meta {attribute}="{re.escape(name)}" content="([^"]*)">', html)
    return html_lib.unescape(match.group(1)) if match else None


def _title(html: str) -> str:
    match = re.search(r"<title>(.*?)</title>", html, flags=re.DOTALL)
    assert match, "title missing"
    return html_lib.unescape(match.group(1))


def test_every_page_template_is_covered():
    from pathlib import Path

    import app.templating as templating

    pages = Path(templating.__file__).parent / "templates" / "pages"
    assert len(PAGES) == len(list(pages.glob("*.html")))


@pytest.mark.parametrize(("path", "expected"), PAGES.items())
def test_page_has_its_own_description(client, path, expected):
    response = client.get(path)
    assert response.status_code == 200
    description = _meta(response.text, "name", "description")
    assert description and description != DEFAULT_DESCRIPTION
    assert expected in description
    assert "  " not in description


def test_descriptions_are_unique(client):
    descriptions = [_meta(client.get(path).text, "name", "description") for path in PAGES]
    assert len(set(descriptions)) == len(PAGES)


@pytest.mark.parametrize("path", PAGES)
def test_open_graph_tags_mirror_the_page(client, path):
    html = client.get(path).text
    assert _meta(html, "property", "og:title") == _title(html)
    assert _meta(html, "property", "og:description") == _meta(html, "name", "description")
    assert _meta(html, "property", "og:url").endswith(path)
    assert _meta(html, "property", "og:site_name") == "F1 Season Calculator"
    assert _meta(html, "property", "og:type") == "website"
    assert _meta(html, "name", "twitter:card") == "summary"


def test_championship_preview_names_the_winner(client):
    html = client.get("/championship/1").text
    assert " wins this " in _meta(html, "name", "description")


@pytest.mark.parametrize(
    ("margin", "runner_up", "ending"),
    [
        (7, "Lando Norris", "by 7 points over Lando Norris."),
        (1, "Lando Norris", "by 1 point over Lando Norris."),
        (0, "Lando Norris", "on a tiebreak over Lando Norris."),
        (0, None, "F1 championship."),
    ],
)
def test_championship_preview_wording(margin, runner_up, ending):
    from app.templating import templates

    template = templates.get_template("pages/championship.html")
    context = template.new_context(
        {
            "current_season": 2026,
            "championship": {
                "driver_names": {"VER": "Max Verstappen"},
                "winner": "VER",
                "num_races": 18,
                "margin": margin,
                "runner_up_name": runner_up,
            },
        }
    )
    description = "".join(template.blocks["description"](context))
    assert description.startswith("Max Verstappen wins this 18-race 2026 ")
    assert description.endswith(ending)


def test_error_pages_keep_the_default_description(client):
    response = client.get("/driver/XXX")
    assert response.status_code >= 400
    assert _meta(response.text, "name", "description") == DEFAULT_DESCRIPTION
