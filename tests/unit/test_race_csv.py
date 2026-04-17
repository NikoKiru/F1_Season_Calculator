"""race_csv: load/save round-trip, sprint-column handling, apply_race splicing."""
from __future__ import annotations

import pytest

from app.pipeline import race_csv


def test_parse_results_valid():
    out = race_csv.parse_results("VER:25, NOR:18,LEC:15")
    assert out == {"VER": 25, "NOR": 18, "LEC": 15}


def test_parse_results_rejects_bad_code():
    with pytest.raises(race_csv.ResultsParseError):
        race_csv.parse_results("VE:25")


def test_parse_results_rejects_non_integer_points():
    with pytest.raises(race_csv.ResultsParseError):
        race_csv.parse_results("VER:twenty")


def test_parse_results_rejects_missing_colon():
    with pytest.raises(race_csv.ResultsParseError):
        race_csv.parse_results("VER25")


def test_parse_results_rejects_empty():
    with pytest.raises(race_csv.ResultsParseError):
        race_csv.parse_results("   ")


def test_load_missing_file_returns_empty(tmp_path):
    drivers, race, sprint = race_csv.load(tmp_path / "nope.csv")
    assert drivers == []
    assert race == {}
    assert sprint == {}


def test_load_reads_sprint_columns(tmp_path):
    csv = tmp_path / "x.csv"
    csv.write_text("Driver,1,2,2s,6,6s\nVER,25,18,8,25,7\nNOR,18,25,6,18,8\n")
    drivers, race, sprint = race_csv.load(csv)
    assert drivers == ["VER", "NOR"]
    assert race["VER"] == {1: 25, 2: 18, 6: 25}
    assert sprint["VER"] == {2: 8, 6: 7}
    assert race["NOR"] == {1: 18, 2: 25, 6: 18}
    assert sprint["NOR"] == {2: 6, 6: 8}


def test_save_then_load_roundtrip(tmp_path):
    csv = tmp_path / "rt.csv"
    drivers = ["VER", "NOR"]
    race = {"VER": {1: 25, 2: 18}, "NOR": {1: 18, 2: 25}}
    sprint = {"VER": {2: 8}, "NOR": {2: 6}}
    race_csv.save(csv, drivers, race, sprint)

    drivers2, race2, sprint2 = race_csv.load(csv)
    assert drivers2 == drivers
    assert race2 == race
    assert sprint2["VER"][2] == 8
    assert sprint2["NOR"][2] == 6


def test_save_omits_sprint_column_when_no_sprint_data(tmp_path):
    csv = tmp_path / "plain.csv"
    race_csv.save(csv, ["VER"], {"VER": {1: 25, 2: 18}}, {})
    text = csv.read_text()
    assert text.splitlines()[0] == "Driver,1,2"


def test_apply_race_adds_new_driver(tmp_path):
    drivers = ["VER"]
    race: dict = {"VER": {1: 25}}
    sprint: dict = {"VER": {}}
    race_csv.apply_race(race, sprint, drivers, 2, {"VER": 18, "HAM": 15})
    assert "HAM" in drivers
    assert race["HAM"][2] == 15
    assert race["VER"][2] == 18


def test_apply_race_zero_fills_missing_drivers(tmp_path):
    drivers = ["VER", "NOR"]
    race: dict = {"VER": {1: 25}, "NOR": {1: 18}}
    sprint: dict = {"VER": {}, "NOR": {}}
    race_csv.apply_race(race, sprint, drivers, 2, {"VER": 25})
    assert race["NOR"][2] == 0


def test_apply_race_with_sprint_zero_fills_sprint(tmp_path):
    drivers = ["VER", "NOR"]
    race: dict = {"VER": {}, "NOR": {}}
    sprint: dict = {"VER": {}, "NOR": {}}
    race_csv.apply_race(
        race, sprint, drivers, 2,
        {"VER": 25, "NOR": 18},
        sprint_results={"VER": 8},
    )
    assert sprint["VER"][2] == 8
    assert sprint["NOR"][2] == 0
