"""Season metadata — replaces championship/models.py with a cleaner API.

Loads data/seasons/{year}.json exactly once per year and hands out immutable
SeasonData objects. No module-level globals — get_season_data(year) is the
only entry point.
"""
import json
from functools import lru_cache

from app.config import get_settings
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
            try:
                years.append(int(f.stem))
            except ValueError:
                pass
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
        )
    driver_names = {code: d.name for code, d in drivers.items()}
    round_names = {int(num): name for num, name in raw["rounds"].items()}

    return SeasonData(
        season=year,
        teams=team_colors,
        drivers=drivers,
        driver_names=driver_names,
        round_names=round_names,
    )


def clear_cache() -> None:
    get_season_data.cache_clear()
    available_seasons.cache_clear()


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
