import json
import os
from typing import Dict, TypedDict, Optional

# Default season for the application
DEFAULT_SEASON = 2026


class DriverInfo(TypedDict):
    """Type definition for driver information."""
    name: str
    team: str
    number: int
    flag: str
    color: str


class SeasonData:
    """Container for season-specific data."""

    def __init__(self, season: int):
        self.season = season
        self._data = load_season_data(season)
        self.team_colors = _build_team_colors(self._data)
        self.drivers = _build_drivers(self._data, self.team_colors)
        self.driver_names = _build_driver_names(self.drivers)
        self.round_names = _build_round_names(self._data)


# Cache for loaded season data
_season_cache: Dict[int, SeasonData] = {}
_available_seasons_cache: Optional[list] = None


def _get_season_config_path(season: int = DEFAULT_SEASON) -> str:
    """Get the path to the season config file."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, 'data', 'seasons', f'{season}.json')


def load_season_data(season: int = DEFAULT_SEASON) -> dict:
    """
    Load season data from a JSON config file.

    Args:
        season: The year of the season to load (default: 2025)

    Returns:
        Dictionary containing teams, drivers, and rounds data

    Raises:
        FileNotFoundError: If the season config file doesn't exist
        json.JSONDecodeError: If the config file is invalid JSON
    """
    config_path = _get_season_config_path(season)

    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def _build_team_colors(season_data: dict) -> Dict[str, str]:
    """Build team colors dictionary from season data."""
    return {team: info['color'] for team, info in season_data['teams'].items()}


def _build_drivers(season_data: dict, team_colors: Dict[str, str]) -> Dict[str, Dict[str, str | int]]:
    """Build drivers dictionary from season data with team colors added."""
    drivers = {}
    for code, info in season_data['drivers'].items():
        drivers[code] = {
            'name': info['name'],
            'team': info['team'],
            'number': info['number'],
            'flag': info['flag'],
            'color': team_colors.get(info['team'], '#FFFFFF')
        }
    return drivers


def _build_round_names(season_data: dict) -> Dict[int, str]:
    """Build round names dictionary from season data."""
    return {int(num): name for num, name in season_data['rounds'].items()}


def _build_driver_names(drivers: Dict[str, Dict[str, str | int]]) -> Dict[str, str]:
    """Build driver names dictionary from drivers data."""
    return {code: info['name'] for code, info in drivers.items()}


def get_season_data(season: Optional[int] = None) -> SeasonData:
    """
    Get season data for the specified year, with caching.

    Args:
        season: The year of the season to load. Defaults to DEFAULT_SEASON.

    Returns:
        SeasonData object containing all season information.
    """
    if season is None:
        season = DEFAULT_SEASON

    if season not in _season_cache:
        _season_cache[season] = SeasonData(season)

    return _season_cache[season]


def clear_season_cache() -> None:
    """Clear the season data cache."""
    global _available_seasons_cache
    _season_cache.clear()
    _available_seasons_cache = None


# Load the default season data for backwards compatibility
_season_data = load_season_data()

# Build the exported dictionaries (backwards compatibility - defaults to 2025)
TEAM_COLORS: Dict[str, str] = _build_team_colors(_season_data)
DRIVERS: Dict[str, Dict[str, str | int]] = _build_drivers(_season_data, TEAM_COLORS)
DRIVER_NAMES: Dict[str, str] = _build_driver_names(DRIVERS)
ROUND_NAMES: Dict[int, str] = _build_round_names(_season_data)


def reload_season_data(season: int = DEFAULT_SEASON) -> None:
    """
    Reload season data from config file.

    This function allows updating the global season data at runtime,
    useful for switching seasons or refreshing after config changes.

    Args:
        season: The year of the season to load
    """
    global TEAM_COLORS, DRIVERS, DRIVER_NAMES, ROUND_NAMES, _season_data, _available_seasons_cache

    _season_data = load_season_data(season)
    TEAM_COLORS = _build_team_colors(_season_data)
    DRIVERS = _build_drivers(_season_data, TEAM_COLORS)
    DRIVER_NAMES = _build_driver_names(DRIVERS)
    ROUND_NAMES = _build_round_names(_season_data)

    # Also update the caches
    _season_cache[season] = SeasonData(season)
    _available_seasons_cache = None


def get_available_seasons() -> list[int]:
    """
    Get list of available season years, with in-memory caching.

    Returns:
        List of season years that have config files, sorted descending (newest first).
    """
    global _available_seasons_cache
    if _available_seasons_cache is not None:
        return _available_seasons_cache

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    seasons_dir = os.path.join(base_dir, 'data', 'seasons')

    if not os.path.exists(seasons_dir):
        return []

    seasons = []
    for filename in os.listdir(seasons_dir):
        if filename.endswith('.json'):
            try:
                season_year = int(filename[:-5])  # Remove .json extension
                seasons.append(season_year)
            except ValueError:
                continue

    _available_seasons_cache = sorted(seasons, reverse=True)
    return _available_seasons_cache
