"""Season metadata — replaces championship/models.py with a cleaner API.

Loads data/seasons/{year}.json exactly once per year and hands out immutable
SeasonData objects. No module-level globals — get_season_data(year) is the
only entry point.
"""
import contextlib
import json
import re
from functools import lru_cache

from app.config import get_settings
from app.domain.constructor import ConstructorInfo
from app.domain.driver import DriverInfo
from app.domain.season import SeasonData


@lru_cache(maxsize=16)
def available_seasons() -> tuple[int, ...]:
    folder = get_settings().seasons_folder
    if not folder.exists():
        return ()
    years: list[int] = []
    for f in folder.iterdir():
        if f.suffix == ".json":
            with contextlib.suppress(ValueError):
                years.append(int(f.stem))
    return tuple(sorted(years, reverse=True))


def default_season() -> int:
    configured = get_settings().default_season
    if configured is not None:
        return configured
    seasons = available_seasons()
    return seasons[0] if seasons else 2026


@lru_cache(maxsize=16)
def get_season_data(season: int | None = None) -> SeasonData:
    year = season if season is not None else default_season()
    path = get_settings().seasons_folder / f"{year}.json"
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)

    team_colors = {name: info["color"] for name, info in raw["teams"].items()}
    drivers: dict[str, DriverInfo] = {}
    for code, info in raw["drivers"].items():
        drivers[code] = DriverInfo(
            name=info["name"],
            team=info["team"],
            number=int(info["number"]),
            flag=info["flag"],
            color=team_colors.get(info["team"], "#FFFFFF"),
            nationality=info.get("nationality"),
            birthdate=info.get("birthdate"),
            debut_year=info.get("debut_year"),
            jolpica_id=info.get("jolpica_id"),
            career=info.get("career"),
        )
    driver_names = {code: d.name for code, d in drivers.items()}
    round_names = {int(num): name for num, name in raw["rounds"].items()}
    sprint_rounds = tuple(int(r) for r in raw.get("sprint_rounds", []))

    constructors: dict[str, ConstructorInfo] = {}
    for name, cinfo in raw.get("constructors", {}).items():
        constructors[name] = ConstructorInfo(
            country=cinfo.get("country"),
            founded=cinfo.get("founded"),
            principal=cinfo.get("principal"),
            power_unit=cinfo.get("power_unit"),
            chassis=cinfo.get("chassis"),
            jolpica_id=cinfo.get("jolpica_id"),
            palmares=cinfo.get("palmares"),
        )

    return SeasonData(
        season=year,
        teams=team_colors,
        drivers=drivers,
        driver_names=driver_names,
        round_names=round_names,
        sprint_rounds=sprint_rounds,
        constructors=constructors,
    )


def clear_cache() -> None:
    get_season_data.cache_clear()
    available_seasons.cache_clear()
    resolve_team_slug.cache_clear()


def resolve_driver_code(raw: str, season: int) -> str:
    """Normalize + validate a driver code against the season's roster.

    Raises ValueError if the code is not known for this season.
    """
    code = raw.strip().upper()
    if len(code) != 3:
        raise ValueError(f"Driver code must be 3 letters, got '{raw}'")
    season_data = get_season_data(season)
    if code not in season_data.drivers:
        raise ValueError(f"Driver '{code}' not found in {season} roster")
    return code


_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def team_slug(name: str) -> str:
    """Lower-case URL slug for a team name. Deterministic, stable per name."""
    lowered = name.strip().lower()
    return _SLUG_NON_ALNUM.sub("-", lowered).strip("-")


@lru_cache(maxsize=128)
def resolve_team_slug(slug: str, season: int) -> str:
    """Reverse `team_slug` against the season's roster.

    Raises ValueError if the slug doesn't match any team in this season.
    """
    target = slug.strip().lower()
    season_data = get_season_data(season)
    for name in season_data.teams:
        if team_slug(name) == target:
            return name
    raise ValueError(f"Constructor '{slug}' not found in {season} roster")


def team_color_for(team_name: str, season: int) -> str:
    season_data = get_season_data(season)
    return season_data.teams.get(team_name, "#666")
