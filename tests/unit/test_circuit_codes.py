"""Circuit-id → round-label map and nationality → flag map."""
from __future__ import annotations

from app.services import circuit_codes, flags


def test_known_circuits_match_current_season_labels():
    # Spot-check against data/seasons/2026.json conventions.
    assert circuit_codes.lookup("albert_park") == "AUS"
    assert circuit_codes.lookup("shanghai") == "CHN"
    assert circuit_codes.lookup("miami") == "MIA"
    assert circuit_codes.lookup("villeneuve") == "CAN"
    assert circuit_codes.lookup("catalunya") == "BAR"
    assert circuit_codes.lookup("madring") == "ESP"
    assert circuit_codes.lookup("rodriguez") == "MXC"
    assert circuit_codes.lookup("interlagos") == "SAP"
    assert circuit_codes.lookup("vegas") == "LVG"
    assert circuit_codes.lookup("yas_marina") == "ABU"


def test_unknown_circuit_returns_none():
    assert circuit_codes.lookup("brand_new_track") is None


def test_fallback_takes_first_three_alpha_chars_uppercased():
    assert circuit_codes.fallback("brand_new_track") == "BRA"
    assert circuit_codes.fallback("a1-ring") == "ARI"


def test_fallback_pads_short_ids():
    assert circuit_codes.fallback("ax") == "AXX"


def test_flags_for_current_grid_nationalities():
    assert flags.flag_for("Dutch") == "🇳🇱"
    assert flags.flag_for("British") == "🇬🇧"
    assert flags.flag_for("Monegasque") == "🇲🇨"
    assert flags.flag_for("Thai") == "🇹🇭"
    assert flags.flag_for("New Zealander") == "🇳🇿"
    assert flags.flag_for("Argentine") == "🇦🇷"


def test_flags_fallback_is_checkered():
    assert flags.flag_for("Martian") == "🏁"
    assert flags.flag_for(None) == "🏁"
