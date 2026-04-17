"""Contract tests for the FastAPI routers."""
from __future__ import annotations


def test_list_championships(client):
    r = client.get("/api/championships", params={"season": 9999, "per_page": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["total_results"] == 15
    assert body["per_page"] == 5
    assert body["season"] == 9999
    assert len(body["results"]) == 5


def test_list_championships_default_season(client):
    r = client.get("/api/championships")
    assert r.status_code == 200
    assert r.json()["season"] == 9999


def test_get_championship_by_id(client):
    r = client.get("/api/championships/1")
    assert r.status_code == 200
    body = r.json()
    assert body["championship_id"] == 1
    assert "driver_points" in body
    assert "round_points_data" in body


def test_get_championship_not_found(client):
    r = client.get("/api/championships/999999999")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "CHAMPIONSHIP_NOT_FOUND"


def test_wins_endpoint(client):
    r = client.get("/api/championships/wins", params={"season": 9999})
    assert r.status_code == 200
    wins = r.json()
    assert sum(wins.values()) == 15


def test_min_races_endpoint(client):
    r = client.get("/api/championships/min-races-to-win", params={"season": 9999})
    assert r.status_code == 200
    body = r.json()
    assert body
    for n in body.values():
        assert 1 <= n <= 4


def test_driver_stats_endpoint(client):
    r = client.get("/api/drivers/VER/stats", params={"season": 9999})
    assert r.status_code == 200
    body = r.json()
    assert body["driver_code"] == "VER"
    assert body["total_championships"] == 15
    assert "head_to_head" in body


def test_driver_stats_unknown_driver(client):
    r = client.get("/api/drivers/XYZ/stats", params={"season": 9999})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "DRIVER_NOT_FOUND"


def test_driver_stats_bad_code_length(client):
    r = client.get("/api/drivers/VE/stats", params={"season": 9999})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "INVALID_DRIVER_CODE"


def test_head_to_head_endpoint(client):
    r = client.get("/api/drivers/head-to-head/VER/NOR", params={"season": 9999})
    assert r.status_code == 200
    body = r.json()
    assert set(body.keys()) == {"VER", "NOR"}


def test_head_to_head_self_is_400(client):
    r = client.get("/api/drivers/head-to-head/VER/VER", params={"season": 9999})
    assert r.status_code == 400


def test_driver_position_pagination(client):
    r = client.get(
        "/api/drivers/VER/position/1",
        params={"season": 9999, "page": 1, "per_page": 3},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["position"] == 1
    assert body["page"] == 1
    assert len(body["championships"]) <= 3


def test_driver_position_invalid_position(client):
    r = client.get("/api/drivers/VER/position/99", params={"season": 9999})
    # /position/99 — 99 > 24 fails path parse via pagination logic (handled at service level)
    # API currently passes 99 through; position 99 should 400 via our custom check
    assert r.status_code in (400, 422)


def test_highest_position_endpoint(client):
    r = client.get("/api/drivers/highest-position", params={"season": 9999})
    assert r.status_code == 200
    rows = r.json()
    drivers = {r["driver"] for r in rows}
    assert drivers == {"VER", "NOR", "LEC"}


def test_positions_endpoint(client):
    r = client.get("/api/drivers/positions", params={"season": 9999, "position": 1})
    assert r.status_code == 200
    rows = r.json()
    total_pct = sum(r["percentage"] for r in rows)
    assert abs(total_pct - 100.0) < 0.1


def test_positions_invalid_position(client):
    r = client.get("/api/drivers/positions", params={"season": 9999, "position": 99})
    assert r.status_code == 422


def test_win_probability_endpoint(client):
    r = client.get("/api/statistics/win-probability", params={"season": 9999})
    assert r.status_code == 200
    body = r.json()
    assert body["season_lengths"] == [1, 2, 3, 4]
    assert body["possible_seasons"] == [4, 6, 4, 1]


def test_search_championship_found(client):
    r = client.get("/api/search/championship", params={"season": 9999, "rounds": "1,2,3,4"})
    assert r.status_code == 200
    body = r.json()
    assert body["championship_id"] > 0
    assert body["url"].startswith("/championship/")


def test_search_championship_invalid_rounds(client):
    r = client.get("/api/search/championship", params={"season": 9999, "rounds": "abc"})
    assert r.status_code == 400


def test_search_championship_out_of_range(client):
    r = client.get("/api/search/championship", params={"season": 9999, "rounds": "99"})
    assert r.status_code == 400


def test_openapi_schema_available(client):
    r = client.get("/api/openapi.json")
    assert r.status_code == 200
    schema = r.json()
    assert "paths" in schema
    assert "/api/championships" in schema["paths"]


def test_validation_error_shape(client):
    r = client.get("/api/championships", params={"page": 0})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "VALIDATION_ERROR"


def test_html_404_renders_page(client):
    r = client.get("/does-not-exist", headers={"accept": "text/html"})
    assert r.status_code == 404
    assert "text/html" in r.headers["content-type"]


def test_api_404_returns_json(client):
    r = client.get("/api/does-not-exist")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
