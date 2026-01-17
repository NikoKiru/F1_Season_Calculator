"""Tests for championship models and season data loading."""
import pytest

from championship.models import (
    load_season_data,
    get_available_seasons,
    get_season_data,
    clear_season_cache,
    SeasonData,
    DEFAULT_SEASON,
    DRIVERS,
    TEAM_COLORS,
    DRIVER_NAMES,
    ROUND_NAMES,
    _build_team_colors,
    _build_drivers,
    _build_round_names,
    _build_driver_names,
)


class TestSeasonDataLoading:
    """Test season data loading from JSON config files."""

    def test_load_season_data_returns_dict(self):
        """Load season data should return a dictionary."""
        data = load_season_data(2025)
        assert isinstance(data, dict)

    def test_load_season_data_has_required_keys(self):
        """Season data should have teams, drivers, and rounds."""
        data = load_season_data(2025)
        assert 'teams' in data
        assert 'drivers' in data
        assert 'rounds' in data
        assert 'season' in data

    def test_load_season_data_has_correct_season(self):
        """Season data should have correct season year."""
        data = load_season_data(2025)
        assert data['season'] == 2025

    def test_load_nonexistent_season_raises_error(self):
        """Loading a non-existent season should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_season_data(1900)


class TestBuiltData:
    """Test the built data dictionaries from season config."""

    def test_team_colors_has_expected_teams(self):
        """TEAM_COLORS should contain all expected F1 teams."""
        expected_teams = [
            'McLaren', 'Red Bull Racing', 'Mercedes', 'Ferrari',
            'Aston Martin', 'Williams', 'Racing Bulls', 'Sauber',
            'Haas', 'Alpine'
        ]
        for team in expected_teams:
            assert team in TEAM_COLORS
            assert TEAM_COLORS[team].startswith('#')

    def test_drivers_has_20_entries(self):
        """DRIVERS should have 20 drivers (F1 grid size)."""
        assert len(DRIVERS) == 20

    def test_drivers_have_required_fields(self):
        """Each driver should have name, team, number, flag, and color."""
        for code, driver in DRIVERS.items():
            assert 'name' in driver
            assert 'team' in driver
            assert 'number' in driver
            assert 'flag' in driver
            assert 'color' in driver
            assert isinstance(driver['number'], int)

    def test_driver_names_matches_drivers(self):
        """DRIVER_NAMES should match DRIVERS entries."""
        assert len(DRIVER_NAMES) == len(DRIVERS)
        for code, name in DRIVER_NAMES.items():
            assert code in DRIVERS
            assert DRIVERS[code]['name'] == name

    def test_round_names_has_24_races(self):
        """ROUND_NAMES should have 24 races."""
        assert len(ROUND_NAMES) == 24

    def test_round_names_has_consecutive_numbers(self):
        """Round numbers should be consecutive from 1 to 24."""
        for i in range(1, 25):
            assert i in ROUND_NAMES
            assert isinstance(ROUND_NAMES[i], str)


class TestDataBuilders:
    """Test the data builder functions."""

    def test_build_team_colors(self):
        """_build_team_colors should extract colors from teams data."""
        season_data = {
            'teams': {
                'TestTeam': {'color': '#FF0000'},
                'AnotherTeam': {'color': '#00FF00'}
            }
        }
        colors = _build_team_colors(season_data)
        assert colors == {'TestTeam': '#FF0000', 'AnotherTeam': '#00FF00'}

    def test_build_drivers(self):
        """_build_drivers should build driver dict with colors."""
        season_data = {
            'drivers': {
                'TST': {
                    'name': 'Test Driver',
                    'team': 'TestTeam',
                    'number': 99,
                    'flag': '\ud83c\udde6\ud83c\uddfa'
                }
            }
        }
        team_colors = {'TestTeam': '#FF0000'}
        drivers = _build_drivers(season_data, team_colors)

        assert 'TST' in drivers
        assert drivers['TST']['name'] == 'Test Driver'
        assert drivers['TST']['team'] == 'TestTeam'
        assert drivers['TST']['number'] == 99
        assert drivers['TST']['color'] == '#FF0000'

    def test_build_round_names(self):
        """_build_round_names should convert string keys to ints."""
        season_data = {
            'rounds': {'1': 'AUS', '2': 'CHN', '3': 'JPN'}
        }
        rounds = _build_round_names(season_data)
        assert rounds == {1: 'AUS', 2: 'CHN', 3: 'JPN'}

    def test_build_driver_names(self):
        """_build_driver_names should extract names from drivers."""
        drivers = {
            'TST': {'name': 'Test Driver', 'team': 'TestTeam'},
            'DRV': {'name': 'Another Driver', 'team': 'AnotherTeam'}
        }
        names = _build_driver_names(drivers)
        assert names == {'TST': 'Test Driver', 'DRV': 'Another Driver'}


class TestGetAvailableSeasons:
    """Test get_available_seasons function."""

    def test_get_available_seasons_returns_list(self):
        """get_available_seasons should return a list."""
        seasons = get_available_seasons()
        assert isinstance(seasons, list)

    def test_get_available_seasons_includes_2025(self):
        """Available seasons should include 2025."""
        seasons = get_available_seasons()
        assert 2025 in seasons

    def test_get_available_seasons_sorted(self):
        """Available seasons should be sorted descending (newest first)."""
        seasons = get_available_seasons()
        assert seasons == sorted(seasons, reverse=True)


class TestSpecificDrivers:
    """Test specific driver data is correct."""

    def test_verstappen_data(self):
        """Max Verstappen data should be correct."""
        assert 'VER' in DRIVERS
        ver = DRIVERS['VER']
        assert ver['name'] == 'Max Verstappen'
        assert ver['team'] == 'Red Bull Racing'
        assert ver['number'] == 1

    def test_norris_data(self):
        """Lando Norris data should be correct."""
        assert 'NOR' in DRIVERS
        nor = DRIVERS['NOR']
        assert nor['name'] == 'Lando Norris'
        assert nor['team'] == 'McLaren'
        assert nor['number'] == 4

    def test_hamilton_data(self):
        """Lewis Hamilton data should be correct."""
        assert 'HAM' in DRIVERS
        ham = DRIVERS['HAM']
        assert ham['name'] == 'Lewis Hamilton'
        assert ham['team'] == 'Ferrari'
        assert ham['number'] == 44


class TestSeasonDataClass:
    """Test the SeasonData class for multi-season support."""

    def test_season_data_loads_2025(self):
        """SeasonData should load 2025 season correctly."""
        season_data = SeasonData(2025)
        assert season_data.season == 2025
        assert len(season_data.drivers) == 20
        assert len(season_data.round_names) == 24

    def test_season_data_loads_2026(self):
        """SeasonData should load 2026 season correctly."""
        season_data = SeasonData(2026)
        assert season_data.season == 2026
        # 2026 has 11 teams with 21 or 22 drivers due to Cadillac expansion
        assert len(season_data.drivers) >= 20
        assert len(season_data.round_names) == 24

    def test_season_data_has_team_colors(self):
        """SeasonData should have team colors."""
        season_data = SeasonData(2025)
        assert len(season_data.team_colors) >= 10

    def test_season_data_has_driver_names(self):
        """SeasonData should have driver names."""
        season_data = SeasonData(2025)
        assert len(season_data.driver_names) == 20
        assert 'VER' in season_data.driver_names


class TestGetSeasonData:
    """Test get_season_data function with caching."""

    def test_get_season_data_default(self):
        """get_season_data should return default season when no arg."""
        clear_season_cache()
        season_data = get_season_data()
        assert season_data.season == DEFAULT_SEASON

    def test_get_season_data_with_year(self):
        """get_season_data should return specified season."""
        clear_season_cache()
        season_data = get_season_data(2026)
        assert season_data.season == 2026

    def test_get_season_data_caching(self):
        """get_season_data should return cached instance."""
        clear_season_cache()
        data1 = get_season_data(2025)
        data2 = get_season_data(2025)
        assert data1 is data2

    def test_get_season_data_different_seasons(self):
        """get_season_data should return different instances for different seasons."""
        clear_season_cache()
        data_2025 = get_season_data(2025)
        data_2026 = get_season_data(2026)
        assert data_2025 is not data_2026
        assert data_2025.season == 2025
        assert data_2026.season == 2026


class TestClearSeasonCache:
    """Test clear_season_cache function."""

    def test_clear_season_cache(self):
        """clear_season_cache should clear the cache."""
        get_season_data(2025)
        get_season_data(2026)
        clear_season_cache()
        # After clearing, new calls should create new instances
        data = get_season_data(2025)
        assert data.season == 2025


class TestMultiSeasonAvailability:
    """Test that multiple seasons are available."""

    def test_both_2025_and_2026_available(self):
        """Both 2025 and 2026 seasons should be available."""
        seasons = get_available_seasons()
        assert 2025 in seasons
        assert 2026 in seasons

    def test_2026_is_first(self):
        """2026 should be first in the list (newest first)."""
        seasons = get_available_seasons()
        assert seasons[0] == 2026
