"""Jolpica schedule endpoint client: transport mocked, no network calls."""
from __future__ import annotations

import httpx
import pytest

from app.services import jolpica_service


def _schedule_payload(races: list[dict]) -> dict:
    return {"MRData": {"RaceTable": {"season": "2026", "Races": races}}}


def _race(
    round_num: str,
    name: str = "Some Grand Prix",
    circuit_id: str = "somewhere",
    country: str = "Nowhere",
    date: str = "2026-03-08",
    sprint: bool = False,
) -> dict:
    race: dict = {
        "round": round_num,
        "raceName": name,
        "date": date,
        "Circuit": {
            "circuitId": circuit_id,
            "Location": {"country": country},
        },
    }
    if sprint:
        race["Sprint"] = {"date": date, "time": "15:00:00Z"}
    return race


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler), base_url="")


def test_fetch_schedule_parses_rounds_and_sprint_flags():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/2026.json" in request.url.path
        return httpx.Response(
            200,
            json=_schedule_payload(
                [
                    _race("1", "Australian Grand Prix", "albert_park", "Australia", "2026-03-08"),
                    _race("2", "Chinese Grand Prix", "shanghai", "China", "2026-03-15", sprint=True),
                ]
            ),
        )

    with _client(handler) as c:
        schedule = jolpica_service.fetch_schedule(2026, client=c)

    assert len(schedule) == 2
    first, second = schedule
    assert first == {
        "round": 1,
        "name": "Australian Grand Prix",
        "circuit_id": "albert_park",
        "country": "Australia",
        "date": "2026-03-08",
        "has_sprint": False,
    }
    assert second["round"] == 2
    assert second["has_sprint"] is True


def test_fetch_schedule_empty_season_raises_round_not_found():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_schedule_payload([]))

    with _client(handler) as c, pytest.raises(jolpica_service.RoundNotFoundError):
        jolpica_service.fetch_schedule(2030, client=c)


def test_fetch_schedule_skips_malformed_rounds():
    def handler(request: httpx.Request) -> httpx.Response:
        races = [
            _race("1"),
            _race("not-a-number"),
            {"round": "3"},  # no Circuit block at all
        ]
        return httpx.Response(200, json=_schedule_payload(races))

    with _client(handler) as c:
        schedule = jolpica_service.fetch_schedule(2026, client=c)

    rounds = [r["round"] for r in schedule]
    assert rounds == [1, 3]
    # Missing Circuit degrades to empty strings, not a crash.
    assert schedule[1]["circuit_id"] == ""
    assert schedule[1]["country"] == ""


def test_fetch_season_drivers_maps_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/2026/drivers.json" in request.url.path
        return httpx.Response(
            200,
            json={
                "MRData": {
                    "DriverTable": {
                        "Drivers": [
                            {
                                "driverId": "lindblad",
                                "permanentNumber": "41",
                                "code": "LIN",
                                "givenName": "Arvid",
                                "familyName": "Lindblad",
                                "dateOfBirth": "2007-08-08",
                                "nationality": "British",
                            },
                            {"driverId": "nocode"},  # skipped: no 3-letter code
                        ]
                    }
                }
            },
        )

    with _client(handler) as c:
        drivers = jolpica_service.fetch_season_drivers(2026, client=c)

    assert drivers == {
        "LIN": {
            "jolpica_id": "lindblad",
            "name": "Arvid Lindblad",
            "number": 41,
            "birthdate": "2007-08-08",
            "nationality": "British",
        }
    }


def test_fetch_driver_constructor_returns_last_constructor_id():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/2026/drivers/lindblad/constructors.json" in request.url.path
        return httpx.Response(
            200,
            json={
                "MRData": {
                    "ConstructorTable": {
                        "Constructors": [
                            {"constructorId": "rb", "name": "RB F1 Team"},
                        ]
                    }
                }
            },
        )

    with _client(handler) as c:
        ctor = jolpica_service.fetch_driver_constructor(2026, "lindblad", client=c)

    assert ctor == "rb"


def test_fetch_driver_constructor_none_when_missing():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"MRData": {"ConstructorTable": {"Constructors": []}}}
        )

    with _client(handler) as c:
        assert jolpica_service.fetch_driver_constructor(2026, "ghost", client=c) is None


def test_fetch_season_constructors_maps_fields():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/2027/constructors.json" in request.url.path
        return httpx.Response(
            200,
            json={
                "MRData": {
                    "ConstructorTable": {
                        "Constructors": [
                            {
                                "constructorId": "audi",
                                "name": "Audi",
                                "nationality": "German",
                            }
                        ]
                    }
                }
            },
        )

    with _client(handler) as c:
        ctors = jolpica_service.fetch_season_constructors(2027, client=c)

    assert ctors == [
        {"jolpica_id": "audi", "name": "Audi", "nationality": "German"}
    ]


def test_fetch_driver_first_season_returns_year():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/drivers/lindblad/seasons.json" in request.url.path
        return httpx.Response(
            200,
            json={
                "MRData": {
                    "SeasonTable": {"Seasons": [{"season": "2026"}]}
                }
            },
        )

    with _client(handler) as c:
        assert jolpica_service.fetch_driver_first_season("lindblad", client=c) == 2026


def test_fetch_driver_first_season_none_on_empty():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"MRData": {"SeasonTable": {"Seasons": []}}})

    with _client(handler) as c:
        assert jolpica_service.fetch_driver_first_season("ghost", client=c) is None
