from fastapi import APIRouter

from app.api.deps import ConnDep, SeasonDep
from app.services import statistics_service

router = APIRouter()


@router.get(
    "/win-probability",
    summary="Championship win probability by driver × season length.",
)
def win_probability(conn: ConnDep, season: SeasonDep) -> dict:
    return statistics_service.win_probability(conn, season)


@router.get(
    "/notable-scenarios",
    summary="Curated 'most extreme' what-if championships for the season.",
)
def notable_scenarios(conn: ConnDep, season: SeasonDep) -> dict:
    return statistics_service.notable_scenarios(conn, season)
