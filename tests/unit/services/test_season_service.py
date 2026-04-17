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
