"""Jolpica-F1 API client — successor to the deprecated Ergast API.

Only used by the `fetch-race` CLI. Returns plain {driver_code: points} dicts
for race and sprint results, so the caller can splice them directly into the
season CSV.

Endpoints:
    GET api.jolpi.ca/ergast/f1/{season}/{round}/results.json
    GET api.jolpi.ca/ergast/f1/{season}/{round}/sprint.json

The API responds with a nested Ergast-compatible structure under
MRData.RaceTable.Races[0].Results. Driver codes are 3-letter uppercase.
"""
from __future__ import annotations

import httpx


BASE_URL = "https://api.jolpi.ca/ergast/f1"
DEFAULT_TIMEOUT = 10.0


class JolpicaError(Exception):
    pass


class RoundNotFoundError(JolpicaError):
    pass


def _extract_results(payload: dict, key: str) -> list[dict]:
    races = payload.get("MRData", {}).get("RaceTable", {}).get("Races", [])
    if not races:
        return []
    return races[0].get(key, [])


def _to_points_map(entries: list[dict]) -> dict[str, int]:
    out: dict[str, int] = {}
    for entry in entries:
        driver = entry.get("Driver") or {}
        code = str(driver.get("code", "")).strip().upper()
        if not code or len(code) != 3:
            continue
        try:
            points = int(float(entry.get("points", "0")))
        except (TypeError, ValueError):
            points = 0
        out[code] = points
    return out


def _fetch(path: str, *, client: httpx.Client | None = None) -> dict:
    url = f"{BASE_URL}{path}"
    owns_client = client is None
    c = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        resp = c.get(url)
        if resp.status_code == 404:
            raise RoundNotFoundError(f"Jolpica 404 for {url}")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as e:
        raise JolpicaError(f"Jolpica request failed: {e}") from e
    finally:
        if owns_client:
            c.close()


def fetch_race(
    season: int, round_number: int, *, client: httpx.Client | None = None
) -> dict[str, int]:
    """Return {driver_code: race_points} for the given season + round."""
    payload = _fetch(f"/{season}/{round_number}/results.json", client=client)
    results = _extract_results(payload, "Results")
    if not results:
        raise RoundNotFoundError(
            f"No race results for season {season} round {round_number}"
        )
    return _to_points_map(results)


def fetch_sprint(
    season: int, round_number: int, *, client: httpx.Client | None = None
) -> dict[str, int]:
    """Return {driver_code: sprint_points}, or empty if this round has no sprint."""
    try:
        payload = _fetch(f"/{season}/{round_number}/sprint.json", client=client)
    except RoundNotFoundError:
        return {}
    results = _extract_results(payload, "SprintResults")
    return _to_points_map(results)


def fetch_weekend(
    season: int, round_number: int, *, client: httpx.Client | None = None
) -> tuple[dict[str, int], dict[str, int]]:
    """Return (race_points, sprint_points) for a weekend. Sprint may be empty."""
    c = client or httpx.Client(timeout=DEFAULT_TIMEOUT)
    try:
        race = fetch_race(season, round_number, client=c)
        sprint = fetch_sprint(season, round_number, client=c)
        return race, sprint
    finally:
        if client is None:
            c.close()
