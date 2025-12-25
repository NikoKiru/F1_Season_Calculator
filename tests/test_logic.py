"""Tests for logic module."""
import pytest
import os
import tempfile
from flask import Flask


@pytest.fixture
def app_with_csv():
    """Create app with test CSV data."""
    from app import app as flask_app

    # Create temp directory and CSV file
    temp_dir = tempfile.mkdtemp()
    csv_path = os.path.join(temp_dir, "championships.csv")

    # Write test CSV data
    with open(csv_path, 'w') as f:
        f.write("Driver,1,2,3\n")
        f.write("VER,25,18,25\n")
        f.write("NOR,18,25,18\n")
        f.write("LEC,15,15,15\n")

    flask_app.config.update({
        "TESTING": True,
        "DATA_FOLDER": temp_dir,
    })

    yield flask_app

    # Cleanup
    try:
        os.remove(csv_path)
        os.rmdir(temp_dir)
    except OSError:
        pass


class TestGetRoundPointsForChampionship:
    """Test get_round_points_for_championship function."""

    def test_get_round_points_valid(self, app_with_csv):
        """Should return points for each driver for specified rounds."""
        from championship.logic import get_round_points_for_championship

        with app_with_csv.app_context():
            result = get_round_points_for_championship(
                drivers=["VER", "NOR", "LEC"],
                round_numbers=[1, 2]
            )

            assert "VER" in result
            assert "NOR" in result
            assert "LEC" in result
            assert result["VER"]["round_points"] == [25, 18]
            assert result["VER"]["total_points"] == 43

    def test_get_round_points_single_round(self, app_with_csv):
        """Should work with a single round."""
        from championship.logic import get_round_points_for_championship

        with app_with_csv.app_context():
            result = get_round_points_for_championship(
                drivers=["VER"],
                round_numbers=[1]
            )

            assert result["VER"]["round_points"] == [25]
            assert result["VER"]["total_points"] == 25

    def test_get_round_points_missing_csv(self, app):
        """Should return empty dict when CSV doesn't exist."""
        from championship.logic import get_round_points_for_championship

        # Set data folder to non-existent path
        app.config["DATA_FOLDER"] = "/nonexistent/path"

        with app.app_context():
            result = get_round_points_for_championship(
                drivers=["VER"],
                round_numbers=[1]
            )

            assert result == {}


class TestCalculateChampionshipFromRounds:
    """Test calculate_championship_from_rounds function."""

    def test_calculate_championship_valid(self, app_with_csv):
        """Should calculate standings from rounds."""
        from championship.logic import calculate_championship_from_rounds

        with app_with_csv.app_context():
            result = calculate_championship_from_rounds([1, 2, 3])

            assert "standings" in result
            assert "points" in result
            assert "winner" in result
            assert result["winner"] == "VER"  # VER has 68 points, NOR has 61

    def test_calculate_championship_partial_rounds(self, app_with_csv):
        """Should work with subset of rounds."""
        from championship.logic import calculate_championship_from_rounds

        with app_with_csv.app_context():
            result = calculate_championship_from_rounds([1])

            assert result["winner"] == "VER"  # VER has 25, NOR has 18

    def test_calculate_championship_missing_csv(self, app):
        """Should return empty dict when CSV doesn't exist."""
        from championship.logic import calculate_championship_from_rounds

        app.config["DATA_FOLDER"] = "/nonexistent/path"

        with app.app_context():
            result = calculate_championship_from_rounds([1, 2])

            assert result == {}
