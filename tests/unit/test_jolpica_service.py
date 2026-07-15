"""Jolpica client: transport mocked via httpx.MockTransport, no network calls."""
from __future__ import annotations

import httpx
import pytest

from app.services import jolpica_service


def _race_payload(results: list[dict]) -> dict:
    return {
        "MRData": {
            "RaceTable": {"Races": [{"Results": results}] if results else []}
        }
    }


def _sprint_payload(results: list[dict]) -> dict:
    return {
        "MRData": {
            "RaceTable": {"Races": [{"SprintResults": results}] if results else []}
        }
    }


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="")


def test_fetch_race_returns_driver_code_to_points():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/2026/3/results.json")
        return httpx.Response(
            200,
            json=_race_payload(
                [
                    {"Driver": {"code": "VER"}, "points": "25"},
                    {"Driver": {"code": "NOR"}, "points": "18"},
                ]
            ),
        )

    with _client(handler) as c:
        result = jolpica_service.fetch_race(2026, 3, client=c)
    assert result == {"VER": 25, "NOR": 18}


def test_fetch_race_404_raises_round_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with _client(handler) as c, pytest.raises(jolpica_service.RoundNotFoundError):
        jolpica_service.fetch_race(2026, 99, client=c)


def test_fetch_race_empty_races_raises_round_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_race_payload([]))

    with _client(handler) as c, pytest.raises(jolpica_service.RoundNotFoundError):
        jolpica_service.fetch_race(2026, 1, client=c)


def test_fetch_sprint_returns_empty_when_no_sprint_round():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with _client(handler) as c:
        result = jolpica_service.fetch_sprint(2026, 1, client=c)
    assert result == {}


def test_fetch_sprint_returns_points_when_present():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/2026/2/sprint.json")
        return httpx.Response(
            200,
            json=_sprint_payload(
                [
                    {"Driver": {"code": "VER"}, "points": "8"},
                    {"Driver": {"code": "NOR"}, "points": "7"},
                ]
            ),
        )

    with _client(handler) as c:
        result = jolpica_service.fetch_sprint(2026, 2, client=c)
    assert result == {"VER": 8, "NOR": 7}


def test_fetch_weekend_returns_race_and_sprint():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/results.json"):
            return httpx.Response(
                200, json=_race_payload([{"Driver": {"code": "VER"}, "points": "25"}])
            )
        return httpx.Response(
            200, json=_sprint_payload([{"Driver": {"code": "VER"}, "points": "8"}])
        )

    with _client(handler) as c:
        race, sprint = jolpica_service.fetch_weekend(2026, 2, client=c)
    assert race == {"VER": 25}
    assert sprint == {"VER": 8}


def test_points_map_skips_malformed_entries():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_race_payload(
                [
                    {"Driver": {"code": "VER"}, "points": "25"},
                    {"Driver": {"code": "XX"}, "points": "10"},         # bad length
                    {"Driver": {}, "points": "5"},                      # no code
                    {"Driver": {"code": "NOR"}, "points": "not-a-num"}, # falls back to 0
                ]
            ),
        )

    with _client(handler) as c:
        result = jolpica_service.fetch_race(2026, 1, client=c)
    assert result == {"VER": 25, "NOR": 0}


def test_network_error_wrapped_as_jolpica_error():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom")

    with _client(handler) as c, pytest.raises(jolpica_service.JolpicaError):
        jolpica_service.fetch_race(2026, 1, client=c)


def test_429_with_http_date_retry_after_backs_off_and_retries(monkeypatch):
    """An HTTP-date Retry-After (RFC 9110) must not crash the retry loop."""
    sleeps: list[float] = []
    monkeypatch.setattr(jolpica_service.time, "sleep", sleeps.append)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] == 1:
            return httpx.Response(
                429, headers={"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, json={}
            )
        return httpx.Response(
            200, json=_race_payload([{"Driver": {"code": "VER"}, "points": "25"}])
        )

    with _client(handler) as c:
        result = jolpica_service.fetch_race(2026, 3, client=c)
    assert result == {"VER": 25}
    assert sleeps == [1]  # exponential-backoff fallback, not a parsed date


def test_429_exhaustion_raises_without_final_sleep(monkeypatch):
    """When every attempt is rate-limited the client must raise straight after
    the last response — sleeping again first just delays the error."""
    sleeps: list[float] = []
    monkeypatch.setattr(jolpica_service.time, "sleep", sleeps.append)
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "2"}, json={})

    with _client(handler) as c, pytest.raises(jolpica_service.JolpicaError):
        jolpica_service.fetch_race(2026, 3, client=c)
    assert calls["n"] == 3  # initial + 2 retries
    assert sleeps == [2.0, 2.0]  # no sleep after the final 429
