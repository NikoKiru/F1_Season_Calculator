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


# --- whole-season results -------------------------------------------------


def _season_page(races: list[dict], *, total: int, offset: int) -> dict:
    return {
        "MRData": {
            "limit": "100",
            "offset": str(offset),
            "total": str(total),
            "RaceTable": {"Races": races},
        }
    }


def _result(code: str, points: int) -> dict:
    return {"Driver": {"code": code}, "points": str(points)}


def test_fetch_season_results_groups_points_by_round():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/2026/results.json")
        return httpx.Response(
            200,
            json=_season_page(
                [
                    {"round": "1", "Results": [_result("VER", 25), _result("NOR", 18)]},
                    {"round": "2", "Results": [_result("NOR", 25), _result("VER", 18)]},
                ],
                total=4,
                offset=0,
            ),
        )

    with _client(handler) as c:
        result = jolpica_service.fetch_season_results(2026, client=c)
    assert result == {1: {"VER": 25, "NOR": 18}, 2: {"NOR": 25, "VER": 18}}


def test_fetch_season_results_joins_a_race_split_across_pages(monkeypatch):
    """Pages hold 100 result rows, so a race usually straddles two of them."""
    monkeypatch.setattr(jolpica_service.time, "sleep", lambda _: None)
    offsets: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["offset"]
        offsets.append(offset)
        assert request.url.params["limit"] == "100"
        if offset == "0":
            races = [{"round": "5", "Results": [_result("VER", 25)]}]
        else:
            races = [
                {"round": "5", "Results": [_result("NOR", 18)]},
                {"round": "6", "Results": [_result("LEC", 25)]},
            ]
        return httpx.Response(200, json=_season_page(races, total=103, offset=int(offset)))

    with _client(handler) as c:
        result = jolpica_service.fetch_season_results(2026, client=c)
    assert offsets == ["0", "100"]
    assert result == {5: {"VER": 25, "NOR": 18}, 6: {"LEC": 25}}


def test_fetch_season_results_is_empty_before_the_first_race():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_season_page([], total=0, offset=0))

    with _client(handler) as c:
        assert jolpica_service.fetch_season_results(2026, client=c) == {}


def test_fetch_season_sprints_reads_sprint_results():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/2026/sprint.json")
        return httpx.Response(
            200,
            json=_season_page(
                [{"round": "2", "SprintResults": [_result("VER", 8), _result("NOR", 7)]}],
                total=2,
                offset=0,
            ),
        )

    with _client(handler) as c:
        assert jolpica_service.fetch_season_sprints(2026, client=c) == {
            2: {"VER": 8, "NOR": 7}
        }


def test_fetch_season_sprints_is_empty_for_a_season_without_sprints():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with _client(handler) as c:
        assert jolpica_service.fetch_season_sprints(2026, client=c) == {}
