from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ConnDep, SeasonDep, validated_driver
from app.services import driver_service


router = APIRouter()


@router.get(
    "/highest-position",
    summary="Best finish position for every driver in a season.",
)
async def highest_position(conn: ConnDep, season: SeasonDep) -> list[dict]:
    return driver_service.highest_position_all(conn, season)


@router.get(
    "/positions",
    summary="How often each driver finished in a given position.",
)
async def positions(
    conn: ConnDep,
    season: SeasonDep,
    position: Annotated[int, Query(ge=1, le=24)],
) -> list[dict]:
    return driver_service.position_summary(conn, position, season)


@router.get(
    "/head-to-head/{driver1}/{driver2}",
    summary="Who finished ahead more often across all shared championships.",
)
async def head_to_head(
    driver1: str,
    driver2: str,
    conn: ConnDep,
    season: SeasonDep,
) -> dict[str, int]:
    d1 = validated_driver(driver1, season)
    d2 = validated_driver(driver2, season)
    try:
        return driver_service.head_to_head(conn, d1, d2, season)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_DRIVER_COMPARISON", "message": str(e)},
        ) from e


@router.get(
    "/{code}/stats",
    summary="Full stats bundle for a driver (one endpoint powers the detail page).",
)
async def driver_stats(
    code: str,
    conn: ConnDep,
    season: SeasonDep,
) -> dict:
    driver = validated_driver(code, season)
    return driver_service.get_stats(conn, driver, season)


@router.get(
    "/{code}/position/{position}",
    summary="Paginated championships where driver finished at a specific position.",
)
async def driver_position_championships(
    code: str,
    position: int,
    conn: ConnDep,
    season: SeasonDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
) -> dict:
    if position < 1 or position > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_POSITION", "message": "Position must be 1–20"},
        )
    driver = validated_driver(code, season)
    return driver_service.championships_at_position(
        conn, driver, position, season, page, per_page
    )
