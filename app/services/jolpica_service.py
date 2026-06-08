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

import time

import httpx

BASE_URL = "https://api.jolpi.ca/ergast/f1"
DEFAULT_TIMEOUT = 10.0
THROTTLE_SECONDS = 0.4  # Jolpica allows 4 req/sec — stay safely under.


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
        for attempt in range(3):  # initial + 2 retries on 429
            resp = c.get(url)
            if resp.status_code == 429:
                # Rate limited — back off and retry. Honor Retry-After if set.
                wait = float(resp.headers.get("Retry-After", 0)) or (2 ** attempt)
                time.sleep(wait)
                continue
            if resp.status_code == 404:
                raise RoundNotFoundError(f"Jolpica 404 for {url}")
            resp.raise_for_status()
            return resp.json()
        raise JolpicaError(f"Jolpica rate-limited after retries: {url}")
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


# --- Bio/career helpers ---------------------------------------------------
#
# The `MRData.total` count trick: every Ergast/Jolpica list endpoint reports
# the total number of matching records in MRData.total. By passing limit=1 we
# pay for just one row of body but read the count from the envelope — far
# cheaper than paging the full result list. Used for career wins, podiums,
# poles, championships, starts.


def _count(path: str, *, client: httpx.Client) -> int | None:
    """Return MRData.total for a list endpoint, or None on failure/404."""
    try:
        payload = _fetch(f"{path}?limit=1", client=client)
    except JolpicaError:
        return None
    try:
        return int(payload.get("MRData", {}).get("total", 0))
    except (TypeError, ValueError):
        return None


def fetch_driver_career(
    jolpica_id: str, *, client: httpx.Client
) -> dict[str, int] | None:
    """Aggregate career totals for a driver. Returns None if not found.

    Championships are NOT fetched: Jolpica requires season_year on
    driverStandings, so counting across all seasons isn't a single query.
    Curate `championships` by hand in seasons/{year}.json — the CLI
    preserves it across refreshes.
    """
    base = f"/drivers/{jolpica_id}"
    starts = _count(f"{base}/results.json", client=client)
    if starts is None:
        return None
    time.sleep(THROTTLE_SECONDS)
    wins = _count(f"{base}/results/1.json", client=client) or 0
    time.sleep(THROTTLE_SECONDS)
    p2 = _count(f"{base}/results/2.json", client=client) or 0
    time.sleep(THROTTLE_SECONDS)
    p3 = _count(f"{base}/results/3.json", client=client) or 0
    time.sleep(THROTTLE_SECONDS)
    poles = _count(f"{base}/qualifying/1.json", client=client) or 0
    return {
        "wins": wins,
        "podiums": wins + p2 + p3,
        "poles": poles,
        "starts": starts,
    }


def fetch_constructor_palmares(
    jolpica_id: str, *, client: httpx.Client
) -> dict[str, int] | None:
    """Aggregate palmarès for a constructor. Returns None if not found.

    `championships` is NOT fetched (same Jolpica limitation as drivers) —
    hand-curate it in seasons/{year}.json.
    """
    base = f"/constructors/{jolpica_id}"
    wins = _count(f"{base}/results/1.json", client=client)
    if wins is None:
        return None
    time.sleep(THROTTLE_SECONDS)
    p2 = _count(f"{base}/results/2.json", client=client) or 0
    time.sleep(THROTTLE_SECONDS)
    p3 = _count(f"{base}/results/3.json", client=client) or 0
    time.sleep(THROTTLE_SECONDS)
    first_race_year: int | None = None
    try:
        seasons_payload = _fetch(f"{base}/seasons.json?limit=1", client=client)
        seasons = (
            seasons_payload.get("MRData", {})
            .get("SeasonTable", {})
            .get("Seasons", [])
        )
        if seasons:
            first_race_year = int(seasons[0].get("season"))
    except (JolpicaError, TypeError, ValueError):
        first_race_year = None
    return {
        "wins": wins,
        "podiums": wins + p2 + p3,
        "first_race_year": first_race_year,
    }
