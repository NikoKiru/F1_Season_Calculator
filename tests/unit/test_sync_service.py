"""Pure sync logic: schedule merging, missing-round planning, count merging."""
from __future__ import annotations

from datetime import date

from app.services import sync_service


def _round(num: int, circuit_id: str, country: str = "", d: str = "2026-03-01", sprint: bool = False) -> dict:
    return {
        "round": num,
        "name": f"GP {num}",
        "circuit_id": circuit_id,
        "country": country,
        "date": d,
        "has_sprint": sprint,
    }


# --- merge_schedule -------------------------------------------------------


def test_merge_adds_missing_future_rounds():
    raw = {"rounds": {"1": "AUS"}, "sprint_rounds": []}
    schedule = [
        _round(1, "albert_park"),
        _round(2, "shanghai", sprint=True),
    ]
    merged, changes = sync_service.merge_schedule(raw, schedule, raced_rounds={1}, raced_sprints=set())
    assert merged["rounds"] == {"1": "AUS", "2": "CHN"}
    assert merged["sprint_rounds"] == [2]
    assert changes  # something was reported


def test_merge_freezes_raced_round_labels():
    # Round 1 was raced under a custom label; the generated label must NOT win.
    raw = {"rounds": {"1": "MEL"}, "sprint_rounds": []}
    schedule = [_round(1, "albert_park")]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds={1}, raced_sprints=set())
    assert merged["rounds"]["1"] == "MEL"


def test_merge_adds_label_for_raced_round_missing_from_json():
    # Raced round with no label yet (e.g. JSON fell behind the CSV): the
    # generated label must be added, never None.
    raw = {"rounds": {}, "sprint_rounds": []}
    schedule = [_round(1, "albert_park")]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds={1}, raced_sprints=set())
    assert merged["rounds"]["1"] == "AUS"


def test_merge_relabels_future_rounds_to_match_schedule():
    # Round 9 hasn't raced; a calendar shuffle renames it.
    raw = {"rounds": {"9": "GBR"}, "sprint_rounds": []}
    schedule = [_round(9, "spa")]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds=set(), raced_sprints=set())
    assert merged["rounds"]["9"] == "BEL"


def test_merge_removes_future_rounds_dropped_from_schedule():
    raw = {"rounds": {"1": "AUS", "22": "ABU"}, "sprint_rounds": []}
    schedule = [_round(1, "albert_park")]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds={1}, raced_sprints=set())
    assert "22" not in merged["rounds"]


def test_merge_keeps_raced_rounds_missing_from_schedule():
    # Historical fact: round 1 was raced even if the API forgot it.
    raw = {"rounds": {"1": "AUS"}, "sprint_rounds": []}
    schedule = [_round(2, "shanghai")]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds={1}, raced_sprints=set())
    assert merged["rounds"]["1"] == "AUS"
    assert merged["rounds"]["2"] == "CHN"


def test_merge_sprint_rounds_are_union_of_schedule_and_raced():
    raw = {"rounds": {}, "sprint_rounds": [2]}
    schedule = [
        _round(1, "albert_park"),
        _round(9, "silverstone", sprint=True),
    ]
    merged, _ = sync_service.merge_schedule(raw, schedule, raced_rounds={2}, raced_sprints={2})
    assert merged["sprint_rounds"] == [2, 9]


def test_merge_no_changes_returns_empty_changelist_and_equal_dict():
    raw = {"rounds": {"1": "AUS"}, "sprint_rounds": []}
    schedule = [_round(1, "albert_park")]
    merged, changes = sync_service.merge_schedule(raw, schedule, raced_rounds=set(), raced_sprints=set())
    assert changes == []
    assert merged == raw


def test_merge_does_not_mutate_input():
    raw = {"rounds": {"1": "AUS"}, "sprint_rounds": []}
    schedule = [_round(1, "albert_park"), _round(2, "shanghai")]
    sync_service.merge_schedule(raw, schedule, raced_rounds=set(), raced_sprints=set())
    assert raw["rounds"] == {"1": "AUS"}


def test_merge_unknown_circuit_falls_back_and_warns():
    raw = {"rounds": {}, "sprint_rounds": []}
    schedule = [_round(3, "brand_new_track", country="Atlantis")]
    merged, changes = sync_service.merge_schedule(raw, schedule, raced_rounds=set(), raced_sprints=set())
    assert merged["rounds"]["3"] == "BRA"  # first 3 letters of circuit id
    assert any("brand_new_track" in c for c in changes)


# --- plan_missing_rounds --------------------------------------------------


def test_plan_returns_completed_rounds_not_in_csv():
    schedule = [
        _round(1, "a", d="2026-03-08"),
        _round(2, "b", d="2026-03-15"),
        _round(3, "c", d="2026-07-04"),  # today — race day counts as due
        _round(4, "d", d="2026-12-06"),  # future
    ]
    missing = sync_service.plan_missing_rounds(
        schedule, csv_rounds={1}, today=date(2026, 7, 4)
    )
    assert missing == [2, 3]


def test_plan_empty_when_up_to_date():
    schedule = [_round(1, "a", d="2026-03-08")]
    assert sync_service.plan_missing_rounds(schedule, {1}, today=date(2026, 7, 4)) == []


def test_plan_skips_rounds_without_a_date():
    schedule = [dict(_round(5, "e"), date="")]
    assert sync_service.plan_missing_rounds(schedule, set(), today=date(2026, 7, 4)) == []


# --- merge_counts ---------------------------------------------------------


def test_merge_counts_stamps_updated_at_on_change():
    existing = {"wins": 5, "updated_at": "old"}
    merged, changed = sync_service.merge_counts(existing, {"wins": 6}, "new")
    assert changed is True
    assert merged["wins"] == 6
    assert merged["updated_at"] == "new"


def test_merge_counts_preserves_timestamp_when_nothing_changed():
    existing = {"wins": 5, "podiums": 10, "championships": 4, "updated_at": "old"}
    merged, changed = sync_service.merge_counts(
        existing, {"wins": 5, "podiums": 10}, "new"
    )
    assert changed is False
    assert merged == existing  # untouched, including updated_at and championships


def test_merge_counts_from_none_counts_as_change():
    merged, changed = sync_service.merge_counts(None, {"wins": 0}, "now")
    assert changed is True
    assert merged == {"wins": 0, "updated_at": "now"}


def test_merge_counts_preserves_hand_curated_keys():
    existing = {"championships": 7, "updated_at": "old"}
    merged, changed = sync_service.merge_counts(existing, {"wins": 106}, "new")
    assert merged["championships"] == 7
    assert merged["wins"] == 106
    assert changed is True


# --- roster_gaps ----------------------------------------------------------


def test_roster_gaps_lists_unknown_codes_sorted():
    raw = {"drivers": {"VER": {}, "NOR": {}}}
    gaps = sync_service.roster_gaps(["NOR", "ZHO", "VER", "LIN"], raw)
    assert gaps == ["LIN", "ZHO"]


def test_roster_gaps_empty_when_all_known():
    raw = {"drivers": {"VER": {}}}
    assert sync_service.roster_gaps(["VER"], raw) == []
