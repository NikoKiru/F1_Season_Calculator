"""Tests for season management CLI commands."""
import os
import csv
import tempfile

import pytest


class TestParseRaceResults:
    """Test the parse_race_results helper function."""

    def test_parse_valid_results(self, app):
        """Should parse valid DRIVER:POINTS pairs."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            result = parse_race_results("VER:25,NOR:18,LEC:15")
            assert result == {'VER': 25, 'NOR': 18, 'LEC': 15}

    def test_parse_empty_string(self, app):
        """Should return empty dict for empty string."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            result = parse_race_results("")
            assert result == {}

    def test_parse_with_spaces(self, app):
        """Should handle whitespace in input."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            result = parse_race_results(" VER : 25 , NOR : 18 ")
            assert result == {'VER': 25, 'NOR': 18}

    def test_parse_invalid_format_no_colon(self, app):
        """Should raise ValueError for missing colon."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            with pytest.raises(ValueError, match="Invalid format"):
                parse_race_results("VER25")

    def test_parse_invalid_points(self, app):
        """Should raise ValueError for non-numeric points."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            with pytest.raises(ValueError, match="Invalid points"):
                parse_race_results("VER:abc")

    def test_parse_invalid_driver_code(self, app):
        """Should raise ValueError for non-3-letter driver code."""
        with app.app_context():
            from championship.season_commands import parse_race_results
            with pytest.raises(ValueError, match="Invalid driver code"):
                parse_race_results("AB:25")


class TestLoadSaveSeasonCSV:
    """Test loading and saving season CSV files."""

    def test_load_nonexistent_csv(self, app):
        """Should return empty data for nonexistent CSV."""
        with app.app_context():
            from championship.season_commands import load_season_csv
            drivers, data = load_season_csv(9999)
            assert drivers == []
            assert data == {}

    def test_save_and_load_season_csv(self, app):
        """Should round-trip save and load season data."""
        with app.app_context():
            from championship.season_commands import save_season_csv, load_season_csv

            # Use a temp directory for DATA_FOLDER to avoid interference
            with tempfile.TemporaryDirectory() as tmpdir:
                app.config['DATA_FOLDER'] = tmpdir

                drivers = ['VER', 'NOR', 'LEC']
                race_data = {
                    'VER': {1: 25, 2: 18},
                    'NOR': {1: 18, 2: 25},
                    'LEC': {1: 15, 2: 15},
                }

                csv_path = save_season_csv(9999, drivers, race_data, 2)
                assert os.path.exists(csv_path)

                loaded_drivers, loaded_data = load_season_csv(9999)
                assert loaded_drivers == ['VER', 'NOR', 'LEC']
                assert loaded_data['VER'][1] == 25
                assert loaded_data['VER'][2] == 18
                assert loaded_data['NOR'][1] == 18


class TestAddRaceCommand:
    """Test the add-race CLI command."""

    def test_add_race_invalid_race_number(self, app):
        """Should reject invalid race number."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'add-race', '--season', '2025',
            '--race', '0', '--results', 'VER:25'
        ])
        assert '[ERROR]' in result.output
        assert 'Invalid race number' in result.output

    def test_add_race_invalid_results(self, app):
        """Should reject invalid result format."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'add-race', '--season', '2025',
            '--race', '1', '--results', 'invalid'
        ])
        assert '[ERROR]' in result.output

    def test_add_race_no_season_config(self, app):
        """Should reject race for nonexistent season."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'add-race', '--season', '9999',
            '--race', '1', '--results', 'VER:25,NOR:18'
        ])
        assert '[ERROR]' in result.output
        assert 'Season config not found' in result.output


class TestClearSeasonCommand:
    """Test the clear-season CLI command."""

    def test_clear_season_no_data(self, app):
        """Should handle clearing season with no data."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'clear-season', '--season', '9999', '--confirm'
        ])
        assert 'No data found' in result.output


class TestSeasonStatusCommand:
    """Test the season-status CLI command."""

    def test_season_status_specific(self, app):
        """Should show status for a specific season."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=['season-status', '--season', '2025'])
        assert 'Season 2025' in result.output
        assert 'Config:' in result.output

    def test_season_status_all(self, app):
        """Should show status for all available seasons."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=['season-status'])
        assert 'Season 2025' in result.output
        assert 'Season 2026' in result.output

    def test_season_status_nonexistent(self, app):
        """Should handle nonexistent season config."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=['season-status', '--season', '9999'])
        assert 'NOT FOUND' in result.output


class TestComputeStatsCommand:
    """Test the compute-stats CLI command (season-aware)."""

    def test_compute_stats_specific_season(self, app):
        """Should compute stats for a specific season."""
        runner = app.test_cli_runner()
        from championship.models import DEFAULT_SEASON
        result = runner.invoke(args=[
            'compute-stats', '--season', str(DEFAULT_SEASON)
        ])
        assert result.exit_code == 0
        assert 'statistics computed' in result.output.lower() or '[OK]' in result.output

    def test_compute_stats_all_seasons(self, app):
        """Should compute stats for all seasons when no season specified."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=['compute-stats'])
        assert result.exit_code == 0
        assert '[OK]' in result.output

    def test_compute_stats_empty_season(self, app):
        """Should handle season with no data."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=['compute-stats', '--season', '9999'])
        assert result.exit_code == 0
        assert 'No championship data' in result.output or '[WARNING]' in result.output


class TestProcessDataCommand:
    """Test the process-data CLI command."""

    def test_process_data_no_csv(self, app):
        """Should error when no CSV exists."""
        runner = app.test_cli_runner()
        result = runner.invoke(args=[
            'process-data', '--season', '9999'
        ])
        assert '[ERROR]' in result.output

    def test_process_data_with_season_csv(self, app):
        """Should process a season-specific CSV."""
        with app.app_context():
            # Use a temp directory for DATA_FOLDER
            with tempfile.TemporaryDirectory() as tmpdir:
                app.config['DATA_FOLDER'] = tmpdir
                csv_path = os.path.join(tmpdir, 'championships_9998.csv')
                with open(csv_path, 'w', newline='') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Driver', '1', '2'])
                    writer.writerow(['VER', '25', '18'])
                    writer.writerow(['NOR', '18', '25'])

                runner = app.test_cli_runner()
                result = runner.invoke(args=[
                    'process-data', '--season', '9998'
                ])
                assert '[OK]' in result.output
