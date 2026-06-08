"""Unit tests for the precomputed `notable_scenarios` table.

These assert the output of `stats_compute` against hand-computed expected
values for the seeded 3-driver x 4-race fixture (see tests/conftest.py):

    VER [25,18,25,18]   NOR [18,25,18,25]   LEC [15,15,15,15]   rounds 1-4

Championship ids are assigned in `race_combinations` order (by size, then
lexicographic):

    {1}=1 {2}=2 {3}=3 {4}=4
    {1,2}=5 {1,3}=6 {1,4}=7 {2,3}=8 {2,4}=9 {3,4}=10
    {1,2,3}=11 {1,2,4}=12 {1,3,4}=13 {2,3,4}=14 {1,2,3,4}=15

Ranking ties keep array order (VER > NOR > LEC) via the writer's stable
argsort, so VER wins every tie on countback.
"""
from __future__ import annotations

import json

from sqlalchemy import text

from app.services import statistics_service

SEASON = 9999


def _row(conn, category: str) -> dict | None:
    r = conn.execute(
        text(
            "SELECT category, championship_id, metric_value, detail "
            "FROM notable_scenarios WHERE season = :s AND category = :c"
        ),
        {"s": SEASON, "c": category},
    ).mappings().one_or_none()
    return dict(r) if r else None


def _detail(row: dict | None) -> dict:
    return json.loads(row["detail"]) if row and row["detail"] else {}


def test_all_five_categories_present(conn):
    cats = conn.execute(
        text("SELECT category FROM notable_scenarios WHERE season = :s"),
        {"s": SEASON},
    ).scalars().all()
    assert set(cats) == {
        "nail_biter",
        "demolition",
        "against_all_odds",
        "cinderella",
        "kingmaker",
    }


def test_nail_biter_is_closest_title(conn):
    # Smallest winner->runner-up gap; tie-break to most races -> the full
    # 4-race scenario (VER 86 vs NOR 86, decided on countback) = id 15.
    row = _row(conn, "nail_biter")
    assert row is not None
    assert row["championship_id"] == 15
    assert row["metric_value"] == 0


def test_demolition_is_biggest_margin(conn):
    # Largest margin = 14; ties {1,3} and {2,4} -> lowest id = {1,3} = id 6.
    row = _row(conn, "demolition")
    assert row is not None
    assert row["championship_id"] == 6
    assert row["metric_value"] == 14


def test_against_all_odds_most_races_with_a_different_champion(conn):
    # Real champion (full season) is VER. The most rounds counted while still
    # crowning someone else = 3-race {1,2,4} won by NOR (lowest id of the two
    # 3-race NOR wins, {1,2,4}=12 and {2,3,4}=14).
    row = _row(conn, "against_all_odds")
    assert row is not None
    assert row["championship_id"] == 12
    assert row["metric_value"] == 3
    assert _detail(row)["real_champion"] == "VER"


def test_cinderella_is_rarest_champion(conn):
    # Title-win counts: VER 10, NOR 5, LEC 0. Rarest champion with >= 1 win is
    # NOR; representative = NOR's best-margin win {2,4} = id 9 (margin 14).
    row = _row(conn, "cinderella")
    assert row is not None
    assert _detail(row)["driver_code"] == "NOR"
    assert row["metric_value"] == 5
    assert row["championship_id"] == 9


def test_kingmaker_is_most_decisive_round(conn):
    # Flips per round: R1=3, R2=2, R3=3, R4=2. Max ties R1/R3 -> lowest = R1.
    # Biggest flipping pair: {2,3,4}(NOR)=id 14 -> {1,2,3,4}(VER)=id 15.
    row = _row(conn, "kingmaker")
    assert row is not None
    detail = _detail(row)
    assert detail["round"] == 1
    assert row["metric_value"] == 3
    assert row["championship_id"] == 15
    assert detail["before_cid"] == 14


# --- service layer (read + format) ----------------------------------------


def test_service_returns_five_scenarios_in_card_order(conn):
    data = statistics_service.notable_scenarios(conn, SEASON)
    cats = [s["category"] for s in data["scenarios"]]
    assert cats == [
        "nail_biter",
        "demolition",
        "against_all_odds",
        "cinderella",
        "kingmaker",
    ]


def test_service_nail_biter_resolves_names_and_margin(conn):
    data = statistics_service.notable_scenarios(conn, SEASON)
    nb = next(s for s in data["scenarios"] if s["category"] == "nail_biter")
    assert nb["championship_id"] == 15
    assert nb["headline"]["winner_name"] == "Max Verstappen"
    assert nb["headline"]["runner_up_name"] == "Lando Norris"
    assert nb["headline"]["margin"] == 0


def test_service_against_all_odds_names_the_real_champion(conn):
    data = statistics_service.notable_scenarios(conn, SEASON)
    odds = next(s for s in data["scenarios"] if s["category"] == "against_all_odds")
    # Headline winner is the upset champion (NOR); the real season champ is VER.
    assert odds["headline"]["winner_name"] == "Lando Norris"
    assert odds["extra"]["real_champion_name"] == "Max Verstappen"


def test_service_cinderella_names_rarest_champion(conn):
    data = statistics_service.notable_scenarios(conn, SEASON)
    c = next(s for s in data["scenarios"] if s["category"] == "cinderella")
    assert c["extra"]["driver_name"] == "Lando Norris"
    assert c["extra"]["driver_color"].startswith("#")


def test_service_kingmaker_resolves_round_and_flip_winners(conn):
    data = statistics_service.notable_scenarios(conn, SEASON)
    k = next(s for s in data["scenarios"] if s["category"] == "kingmaker")
    assert k["extra"]["round"] == 1
    assert k["extra"]["before_winner_name"] == "Lando Norris"
    assert k["extra"]["after_winner_name"] == "Max Verstappen"
