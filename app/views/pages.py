"""SSR page controllers — every HTML route lives here.

Views compose services and pass shaped context to Jinja. No DB access sits
directly in this module — that's the whole point of the services layer.
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.api.deps import ConnDep, SeasonDep, validated_driver
from app.services import (
    championship_service,
    driver_service,
    season_service,
    statistics_service,
)
from app.templating import render


router = APIRouter()


# --- context helpers ----------------------------------------------------


def _common(season: int) -> dict:
    return {
        "current_season": season,
        "seasons": list(season_service.available_seasons()),
    }


def _breadcrumbs(*segments: tuple[str, str | None]) -> list[dict]:
    return [{"label": label, "href": href} for label, href in segments]


# --- routes -------------------------------------------------------------


@router.get("/", include_in_schema=False)
def home(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    wins = championship_service.all_wins(conn, season)

    # Current standings derived from full-season row: load page 1 filtered
    # to the max-length championship so points match the "final" scenario.
    max_champ = next(
        (r for r in championship_service.get_page(conn, season, 1, 1)["results"]),
        None,
    )

    context = {
        **_common(season),
        "drivers": [
            {
                "code": code,
                "name": d.name,
                "team": d.team,
                "color": d.color,
                "wins": wins.get(code, 0),
            }
            for code, d in sd.drivers.items()
        ],
        "featured_championship": max_champ,
        "page_data": {
            "rounds": list(sd.round_names.values()),
            "drivers": [
                {"code": code, "color": d.color, "cumulative": []}
                for code, d in sd.drivers.items()
            ],
        },
    }
    return render(request, "pages/index.html", context)


@router.get("/drivers", include_in_schema=False)
def drivers_page(request: Request, season: SeasonDep):
    sd = season_service.get_season_data(season)
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Drivers", None)),
        "drivers": [
            {"code": code, "name": d.name, "team": d.team, "color": d.color}
            for code, d in sd.drivers.items()
        ],
    }
    return render(request, "pages/drivers.html", context)


@router.get("/driver/{code}", include_in_schema=False)
def driver_page(request: Request, code: str, conn: ConnDep, season: SeasonDep):
    driver_code = validated_driver(code, season)
    stats = driver_service.get_stats(conn, driver_code, season)
    sd = season_service.get_season_data(season)
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(
            ("Home", "/"),
            ("Drivers", "/drivers"),
            (stats["driver_name"], None),
        ),
        "driver": stats["driver_info"] | {"code": driver_code, "name": stats["driver_name"]},
        "stats": stats,
        "other_drivers": [
            {"code": c, "name": d.name, "color": d.color}
            for c, d in sd.drivers.items() if c != driver_code
        ],
        "page_data": {
            "driver_code": driver_code,
            "season": season,
            "color": stats["driver_info"]["color"],
        },
    }
    return render(request, "pages/driver.html", context)


@router.get("/driver/{code}/position/{position}", include_in_schema=False)
def driver_position_detail(
    request: Request,
    code: str,
    position: int,
    conn: ConnDep,
    season: SeasonDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=500)] = 50,
):
    if position < 1 or position > 20:
        raise HTTPException(status_code=400, detail="Position must be 1–20")
    driver_code = validated_driver(code, season)
    data = driver_service.championships_at_position(
        conn, driver_code, position, season, page, per_page
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(
            ("Home", "/"),
            ("Drivers", "/drivers"),
            (data["driver_name"], f"/driver/{driver_code}"),
            (f"P{position}", None),
        ),
        "data": data,
        "position": position,
        "driver_code": driver_code,
    }
    return render(request, "pages/driver_position_detail.html", context)


@router.get("/championship/{championship_id}", include_in_schema=False)
def championship_page(request: Request, championship_id: int, conn: ConnDep):
    data = championship_service.get_by_id(conn, championship_id)
    if data is None:
        raise HTTPException(status_code=404, detail="Championship not found")
    season = int(data["season"])
    sd = season_service.get_season_data(season)

    driver_points = data.get("driver_points", {}) or {}
    ordered = list(driver_points.keys())
    # Cumulative-by-round chart data
    round_points = data.get("round_points_data", {}) or {}
    rounds = data.get("round_names", []) or []
    drivers_payload = []
    for code in ordered:
        per_round = round_points.get(code, {}).get("round_points", [])
        cumulative: list[int] = []
        running = 0
        for p in per_round:
            running += int(p)
            cumulative.append(running)
        drivers_payload.append(
            {"code": code, "color": sd.drivers.get(code).color if code in sd.drivers else "#666", "cumulative": cumulative}
        )

    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), (f"Championship #{championship_id}", None)),
        "championship": data,
        "page_data": {"rounds": rounds, "drivers": drivers_payload},
    }
    return render(request, "pages/championship.html", context)


@router.get("/create-championship", include_in_schema=False)
def create_championship_page(request: Request, season: SeasonDep):
    sd = season_service.get_season_data(season)
    rounds = [
        {"number": num, "name": name, "sprint": sd.is_sprint(num)}
        for num, name in sorted(sd.round_names.items())
    ]
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Create", None)),
        "rounds": rounds,
        "page_data": {"season": season, "total_rounds": len(rounds)},
    }
    return render(request, "pages/create_championship.html", context)


@router.get("/championship-win-probability", include_in_schema=False)
def win_probability_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    data = statistics_service.win_probability(conn, season)
    for row in data["drivers_data"]:
        row["name"] = sd.driver_names.get(row["driver"], row["driver"])
        row["color"] = sd.drivers[row["driver"]].color if row["driver"] in sd.drivers else "#666"
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Win probability", None)),
        "data": data,
    }
    return render(request, "pages/championship_win_probability.html", context)


@router.get("/all-championship-wins", include_in_schema=False)
def all_wins_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    wins = championship_service.all_wins(conn, season)
    ranked = sorted(
        [
            {
                "code": code,
                "name": sd.driver_names.get(code, code),
                "color": sd.drivers[code].color if code in sd.drivers else "#666",
                "wins": count,
            }
            for code, count in wins.items()
        ],
        key=lambda r: r["wins"],
        reverse=True,
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("All championship wins", None)),
        "drivers": ranked,
    }
    return render(request, "pages/all_championship_wins.html", context)


@router.get("/highest-position", include_in_schema=False)
def highest_position_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    rows = driver_service.highest_position_all(conn, season)
    ranked = sorted(
        [
            {
                **r,
                "name": sd.driver_names.get(r["driver"], r["driver"]),
                "color": sd.drivers[r["driver"]].color if r["driver"] in sd.drivers else "#666",
            }
            for r in rows
        ],
        key=lambda r: (r["position"], -1 * (r["best_margin"] or 0)),
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Highest position", None)),
        "rows": ranked,
    }
    return render(request, "pages/highest_position.html", context)


@router.get("/driver-positions", include_in_schema=False)
def driver_positions_page(request: Request, season: SeasonDep):
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Positions", None)),
        "positions": list(range(1, 21)),
        "page_data": {"season": season},
    }
    return render(request, "pages/driver_positions.html", context)


@router.get("/head-to-head", include_in_schema=False)
def head_to_head_page(request: Request, season: SeasonDep):
    sd = season_service.get_season_data(season)
    drivers = [
        {"code": code, "name": d.name, "team": d.team, "color": d.color}
        for code, d in sd.drivers.items()
    ]
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Head-to-head", None)),
        "drivers": drivers,
        "page_data": {"season": season, "drivers": drivers},
    }
    return render(request, "pages/head_to_head.html", context)


@router.get("/min-races-to-win", include_in_schema=False)
def min_races_to_win_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    data = championship_service.min_races_to_win(conn, season)
    ranked = sorted(
        [
            {
                "code": code,
                "name": sd.driver_names.get(code, code),
                "color": sd.drivers[code].color if code in sd.drivers else "#666",
                "min_races": races,
            }
            for code, races in data.items()
        ],
        key=lambda r: r["min_races"],
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Minimum races", None)),
        "rows": ranked,
    }
    return render(request, "pages/min_races_to_win.html", context)
