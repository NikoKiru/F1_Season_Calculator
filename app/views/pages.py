"""SSR page controllers — every HTML route lives here.

Views compose services and pass shaped context to Jinja. No DB access sits
directly in this module — that's the whole point of the services layer.
"""
from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request

from app.api.deps import ConnDep, SeasonDep, validated_driver
from app.services import (
    championship_service,
    constructor_service,
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

    first = next(
        iter(championship_service.get_page(conn, season, 1, 1)["results"]), None
    )
    max_champ = (
        championship_service.get_by_id(conn, int(first["championship_id"]))
        if first
        else None
    )

    driver_points = (max_champ or {}).get("driver_points", {}) or {}
    round_points = (max_champ or {}).get("round_points_data", {}) or {}
    rounds = (max_champ or {}).get("round_names", []) or []

    # Standings are already sorted DESC by points — the DB's `standings` column
    # is the ordered list. Fall back to season JSON order when no data yet.
    ordered_codes = list(driver_points.keys()) or list(sd.drivers.keys())
    drivers_view = [
        {
            "code": code,
            "name": sd.drivers[code].name if code in sd.drivers else code,
            "team": sd.drivers[code].team if code in sd.drivers else "",
            "color": sd.drivers[code].color if code in sd.drivers else "#666",
            "nationality": sd.drivers[code].nationality if code in sd.drivers else None,
            "wins": wins.get(code, 0),
            "points": driver_points.get(code, 0),
        }
        for code in ordered_codes
    ]

    chart_drivers = []
    for code in ordered_codes[:5]:
        per_round = (round_points.get(code) or {}).get("round_points") or []
        cumulative: list[int] = []
        running = 0
        for p in per_round:
            running += int(p)
            cumulative.append(running)
        chart_drivers.append(
            {
                "code": code,
                "team": sd.drivers[code].team if code in sd.drivers else "",
                "color": sd.drivers[code].color if code in sd.drivers else "#666",
                "cumulative": cumulative,
            }
        )

    live_championship_id = int(first["championship_id"]) if first else None

    context = {
        **_common(season),
        "drivers": drivers_view,
        "featured_championship": max_champ,
        "live_championship_id": live_championship_id,
        "page_data": {"rounds": rounds, "drivers": chart_drivers},
    }
    return render(request, "pages/index.html", context)


@router.get("/drivers", include_in_schema=False)
def drivers_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)

    # Sort drivers by live points (full-enumeration scenario standings).
    first = next(
        iter(championship_service.get_page(conn, season, 1, 1)["results"]), None
    )
    live_points: dict[str, int] = {}
    if first:
        live = championship_service.get_by_id(conn, int(first["championship_id"]))
        live_points = (live or {}).get("driver_points", {}) or {}

    drivers = [
        {
            "code": code,
            "name": d.name,
            "team": d.team,
            "color": d.color,
            "nationality": d.nationality,
            "points": int(live_points.get(code, 0)),
        }
        for code, d in sd.drivers.items()
    ]
    drivers.sort(key=lambda x: -x["points"])

    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Drivers", None)),
        "drivers": drivers,
    }
    return render(request, "pages/drivers.html", context)


@router.get("/driver/{code}", include_in_schema=False)
def driver_page(request: Request, code: str, conn: ConnDep, season: SeasonDep):
    driver_code = validated_driver(code, season)
    stats = driver_service.get_stats(conn, driver_code, season)
    sd = season_service.get_season_data(season)
    driver = stats["driver_info"] | {"code": driver_code, "name": stats["driver_name"]}
    bd = driver.get("birthdate")
    driver["age"] = _years_between(bd, date.today()) if bd else None
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(
            ("Home", "/"),
            ("Drivers", "/drivers"),
            (stats["driver_name"], None),
        ),
        "driver": driver,
        "career": driver.get("career"),
        "stats": stats,
        "driver_names": sd.driver_names,
        "driver_colors": {c: d.color for c, d in sd.drivers.items()},
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


def _years_between(start: date, end: date) -> int:
    """Whole years from start to end (correct across leap-year birthdays)."""
    years = end.year - start.year
    if (end.month, end.day) < (start.month, start.day):
        years -= 1
    return years


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
    # get_by_id returns the TTL-cached dict itself — copy before decorating
    # with view-only keys, or they leak into /api/championships/{id}.
    data = dict(data)
    season = int(data["season"])
    sd = season_service.get_season_data(season)

    driver_points = data.get("driver_points", {}) or {}
    ordered = list(driver_points.keys())

    winner_code = data.get("winner")
    margin = 0
    runner_up_name: str | None = None
    if len(ordered) >= 2:
        points_list = list(driver_points.values())
        margin = int(points_list[0]) - int(points_list[1])
        runner_up_code = ordered[1]
        runner_up_name = data.get("driver_names", {}).get(runner_up_code, runner_up_code)
    data["margin"] = margin
    data["runner_up_name"] = runner_up_name
    data["winner_color"] = sd.drivers[winner_code].color if winner_code in sd.drivers else "#666"
    data["winner_team"] = sd.drivers[winner_code].team if winner_code in sd.drivers else ""
    data["driver_colors"] = {
        code: (sd.drivers[code].color if code in sd.drivers else "#666")
        for code in ordered
    }

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
            {
                "code": code,
                "team": sd.drivers[code].team if code in sd.drivers else "",
                "color": sd.drivers.get(code).color if code in sd.drivers else "#666",
                "cumulative": cumulative,
            }
        )

    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), (f"Championship #{championship_id}", None)),
        "championship": data,
        "page_data": {"rounds": rounds, "drivers": drivers_payload},
    }
    return render(request, "pages/championship.html", context)


@router.get("/create-championship", include_in_schema=False)
def create_championship_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    # Only raced rounds exist in the championships table — future rounds are
    # rendered locked so a selection can never 404 on search.
    raced = set(championship_service.raced_rounds(conn, season))
    rounds = [
        {
            "number": num,
            "name": name,
            "sprint": sd.is_sprint(num),
            "raced": num in raced,
        }
        for num, name in sorted(sd.round_names.items())
    ]
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Create", None)),
        "rounds": rounds,
        "raced_count": len(raced),
        "page_data": {"season": season, "total_rounds": len(rounds)},
    }
    return render(request, "pages/create_championship.html", context)


@router.get("/championship-win-probability", include_in_schema=False)
def win_probability_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    data = statistics_service.win_probability(conn, season)
    # Copy rows before decorating — the rows live in the TTL cache and the
    # bare /api/statistics/win-probability response must keep its shape.
    data = dict(data)
    data["drivers_data"] = [
        {
            **row,
            "name": sd.driver_names.get(row["driver"], row["driver"]),
            "color": sd.drivers[row["driver"]].color if row["driver"] in sd.drivers else "#666",
        }
        for row in data["drivers_data"]
    ]
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
                "team": sd.drivers[r["driver"]].team if r["driver"] in sd.drivers else "",
                "color": sd.drivers[r["driver"]].color if r["driver"] in sd.drivers else "#666",
                "scenario_id": r.get("best_margin_championship_id") or r.get("max_races_championship_id"),
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
    sd = season_service.get_season_data(season)
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Positions", None)),
        "positions": list(range(1, 21)),
        "page_data": {
            "season": season,
            "driver_names": sd.driver_names,
            "driver_colors": {c: d.color for c, d in sd.drivers.items()},
        },
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


@router.get("/notable-scenarios", include_in_schema=False)
def notable_scenarios_page(request: Request, conn: ConnDep, season: SeasonDep):
    data = statistics_service.notable_scenarios(conn, season)
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Notable scenarios", None)),
        "scenarios": data["scenarios"],
    }
    return render(request, "pages/notable_scenarios.html", context)


# --- constructors (WCC) ---------------------------------------------------


def _constructor_row(name: str, sd, *, extras: dict | None = None) -> dict:
    base = {
        "name": name,
        "slug": season_service.team_slug(name),
        "color": sd.teams.get(name, "#666"),
    }
    if extras:
        base.update(extras)
    return base


@router.get("/constructors", include_in_schema=False)
def constructors_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    live = constructor_service.live_points(conn, season)
    wins = constructor_service.all_wins(conn, season)
    constructors = [
        _constructor_row(
            name, sd,
            extras={"points": int(live.get(name, 0)), "wins": int(wins.get(name, 0))},
        )
        for name in sd.teams
    ]
    constructors.sort(key=lambda c: -c["points"])
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Constructors", None)),
        "constructors": constructors,
    }
    return render(request, "pages/constructors.html", context)


@router.get("/all-constructor-wins", include_in_schema=False)
def all_constructor_wins_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    wins = constructor_service.all_wins(conn, season)
    ranked = sorted(
        [
            _constructor_row(name, sd, extras={"wins": count})
            for name, count in wins.items()
        ],
        key=lambda r: r["wins"],
        reverse=True,
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("All constructor wins", None)),
        "constructors": ranked,
    }
    return render(request, "pages/all_constructor_wins.html", context)


@router.get("/constructor-win-probability", include_in_schema=False)
def constructor_win_probability_page(
    request: Request, conn: ConnDep, season: SeasonDep
):
    sd = season_service.get_season_data(season)
    data = constructor_service.win_probability(conn, season)
    # Same cache-isolation copy as the driver win-probability page.
    data = dict(data)
    data["constructors_data"] = [
        {
            **row,
            "slug": season_service.team_slug(row["constructor"]),
            "color": sd.teams.get(row["constructor"], "#666"),
        }
        for row in data["constructors_data"]
    ]
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Constructor win probability", None)),
        "data": data,
    }
    return render(request, "pages/constructor_win_probability.html", context)


@router.get("/constructor-min-races-to-win", include_in_schema=False)
def constructor_min_races_page(request: Request, conn: ConnDep, season: SeasonDep):
    sd = season_service.get_season_data(season)
    data = constructor_service.min_races_to_win(conn, season)
    ranked = sorted(
        [
            _constructor_row(name, sd, extras={"min_races": races})
            for name, races in data.items()
        ],
        key=lambda r: r["min_races"],
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Min races to clinch", None)),
        "rows": ranked,
    }
    return render(request, "pages/constructor_min_races_to_win.html", context)


@router.get("/constructor-highest-position", include_in_schema=False)
def constructor_highest_position_page(
    request: Request, conn: ConnDep, season: SeasonDep
):
    sd = season_service.get_season_data(season)
    rows = constructor_service.highest_position_all(conn, season)
    ranked = sorted(
        [
            {
                **r,
                "name": r["constructor"],
                "slug": season_service.team_slug(r["constructor"]),
                "color": sd.teams.get(r["constructor"], "#666"),
                "scenario_id": r.get("best_margin_championship_id")
                              or r.get("max_races_championship_id"),
            }
            for r in rows
        ],
        key=lambda r: (r["position"], -1 * (r["best_margin"] or 0)),
    )
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Constructor highest position", None)),
        "rows": ranked,
    }
    return render(request, "pages/constructor_highest_position.html", context)


@router.get("/constructor/{slug}", include_in_schema=False)
def constructor_page(request: Request, slug: str, conn: ConnDep, season: SeasonDep):
    try:
        name = season_service.resolve_team_slug(slug, season)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    sd = season_service.get_season_data(season)
    stats = constructor_service.get_stats(conn, name, season)
    constructor_slugs = {n: season_service.team_slug(n) for n in sd.teams}
    constructor_colors = dict(sd.teams)
    ctor = sd.constructors.get(name)
    identity = ctor.model_dump(exclude={"palmares"}) if ctor else None
    palmares = ctor.palmares.model_dump() if ctor and ctor.palmares else None
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(
            ("Home", "/"),
            ("Constructors", "/constructors"),
            (name, None),
        ),
        "constructor": {
            "name": name,
            "slug": slug,
            "color": sd.teams.get(name, "#666"),
        },
        "identity": identity,
        "palmares": palmares,
        "stats": stats,
        "constructor_slugs": constructor_slugs,
        "constructor_colors": constructor_colors,
        "page_data": {
            "slug": slug,
            "season": season,
            "color": sd.teams.get(name, "#666"),
        },
    }
    return render(request, "pages/constructor.html", context)


@router.get("/constructor/{slug}/position/{position}", include_in_schema=False)
def constructor_position_detail(
    request: Request,
    slug: str,
    position: int,
    conn: ConnDep,
    season: SeasonDep,
    page: Annotated[int, Query(ge=1)] = 1,
    per_page: Annotated[int, Query(ge=1, le=500)] = 50,
):
    if position < 1:
        raise HTTPException(status_code=400, detail="Position must be ≥ 1")
    try:
        name = season_service.resolve_team_slug(slug, season)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    data = constructor_service.championships_at_position(
        conn, name, position, season, page, per_page
    )
    data["constructor_name"] = name
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(
            ("Home", "/"),
            ("Constructors", "/constructors"),
            (name, f"/constructor/{slug}"),
            (f"P{position}", None),
        ),
        "data": data,
        "position": position,
        "slug": slug,
    }
    return render(request, "pages/constructor_position_detail.html", context)


@router.get("/constructor-positions", include_in_schema=False)
def constructor_positions_page(request: Request, season: SeasonDep):
    sd = season_service.get_season_data(season)
    num_constructors = max(len(sd.teams), 1)
    context = {
        **_common(season),
        "crumbs": _breadcrumbs(("Home", "/"), ("Constructor positions", None)),
        "positions": list(range(1, num_constructors + 1)),
        "page_data": {
            "season": season,
            "constructor_names": {
                season_service.team_slug(name): name for name in sd.teams
            },
            "constructor_colors": {
                season_service.team_slug(name): color for name, color in sd.teams.items()
            },
        },
    }
    return render(request, "pages/constructor_positions.html", context)
