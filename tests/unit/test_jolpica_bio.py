"""Jolpica bio/career helpers — transport mocked, no network."""
from __future__ import annotations

import httpx
import pytest

from app.services import jolpica_service


@pytest.fixture(autouse=True)
def _no_throttle(monkeypatch):
    monkeypatch.setattr(jolpica_service, "THROTTLE_SECONDS", 0)


def _total(n: int) -> dict:
    return {"MRData": {"total": str(n)}}


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="")


def test_fetch_driver_career_aggregates_counts():
    # Counts: starts=350, p1=63, p2=40, p3=30, poles=104
    # championships intentionally NOT fetched (hand-curated in JSON).
    by_path = {
        "/drivers/hamilton/results.json": 350,
        "/drivers/hamilton/results/1.json": 63,
        "/drivers/hamilton/results/2.json": 40,
        "/drivers/hamilton/results/3.json": 30,
        "/drivers/hamilton/qualifying/1.json": 104,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        for path, count in by_path.items():
            if request.url.path.endswith(path):
                return httpx.Response(200, json=_total(count))
        return httpx.Response(404, json={})

    with _client(handler) as c:
        result = jolpica_service.fetch_driver_career("hamilton", client=c)

    assert result == {
        "wins": 63,
        "podiums": 63 + 40 + 30,
        "poles": 104,
        "starts": 350,
    }


def test_fetch_driver_career_returns_none_when_starts_404():
    """If the first probe 404s, treat the whole driver as unknown."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with _client(handler) as c:
        assert jolpica_service.fetch_driver_career("not_a_driver", client=c) is None


def test_fetch_constructor_palmares_aggregates_counts():
    by_path = {
        "/constructors/ferrari/results/1.json": 248,
        "/constructors/ferrari/results/2.json": 200,
        "/constructors/ferrari/results/3.json": 180,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/seasons.json"):
            return httpx.Response(
                200,
                json={"MRData": {"SeasonTable": {"Seasons": [{"season": "1950"}]}}},
            )
        for prefix, count in by_path.items():
            if path.endswith(prefix):
                return httpx.Response(200, json=_total(count))
        return httpx.Response(404, json={})

    with _client(handler) as c:
        result = jolpica_service.fetch_constructor_palmares("ferrari", client=c)

    assert result == {
        "wins": 248,
        "podiums": 248 + 200 + 180,
        "first_race_year": 1950,
    }


def test_fetch_constructor_palmares_returns_none_when_wins_404():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with _client(handler) as c:
        assert jolpica_service.fetch_constructor_palmares("nope", client=c) is None
