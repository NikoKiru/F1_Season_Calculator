from app.services import season_service


def test_available_seasons_includes_test_season(seeded_settings):
    seasons = season_service.available_seasons()
    assert 9999 in seasons


def test_default_season_is_configured(seeded_settings):
    assert season_service.default_season() == 9999


def test_get_season_data_roster(seeded_settings):
    sd = season_service.get_season_data(9999)
    assert set(sd.drivers) == {"VER", "NOR", "LEC"}
    assert sd.drivers["VER"].team == "Red Bull"
    assert sd.drivers["VER"].color == "#3671C6"
    assert sd.round_names[1] == "Round 1"


def test_resolve_driver_code_normalizes(seeded_settings):
    assert season_service.resolve_driver_code(" ver ", 9999) == "VER"


def test_resolve_driver_code_unknown(seeded_settings):
    import pytest
    with pytest.raises(ValueError):
        season_service.resolve_driver_code("XYZ", 9999)


def test_resolve_driver_code_bad_length(seeded_settings):
    import pytest
    with pytest.raises(ValueError):
        season_service.resolve_driver_code("VE", 9999)


def test_2026_round_calendar_is_sequential():
    """Regression: 2026.json used to call Miami round 6 (real F1 calendar
    number) while the CSV listed it as round 4 (sequential order of the
    races actually held). The mismatch made the home-page chart label
    Miami as 'Unknown'. The JSON now uses sequential numbering: 4 = MIA."""
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    raw = json.loads((repo_root / "data" / "seasons" / "2026.json").read_text(encoding="utf-8"))
    rounds = {int(k): v for k, v in raw["rounds"].items()}
    sprint_rounds = list(raw["sprint_rounds"])

    # Sequential: keys must be 1..N with no gaps.
    assert sorted(rounds) == list(range(1, len(rounds) + 1))
    # Miami sits at the 4th race held this season.
    assert rounds[4] == "MIA"
    # Sprint rounds also use the sequential numbering.
    assert 4 in sprint_rounds
    assert all(1 <= r <= len(rounds) for r in sprint_rounds)
