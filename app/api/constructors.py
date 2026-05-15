"""JSON endpoints for the constructors' championship (WCC)."""
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ConnDep, SeasonDep
from app.services import constructor_service, season_service

router = APIRouter()


def _resolved_constructor(slug: str, season: int) -> str:
    try:
        return season_service.resolve_team_slug(slug, season)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CONSTRUCTOR_NOT_FOUND", "message": str(e)},
        ) from e


@router.get(
    "/highest-position",
    summary="Best WCC finish position for every constructor in a season.",
)
async def highest_position(conn: ConnDep, season: SeasonDep) -> list[dict]:
    return constructor_service.highest_position_all(conn, season)


@router.get(
    "/positions",
    summary="How often each constructor finished in a given position.",
)
async def positions(
    conn: ConnDep,
    season: SeasonDep,
    position: Annotated[int, Query(ge=1, le=24)],
) -> list[dict]:
    return constructor_service.position_summary(conn, position, season)


@router.get(
    "/head-to-head/{c1}/{c2}",
    summary="Who finished ahead more often across all shared championships (WCC).",
)
async def head_to_head(
    c1: str,
    c2: str,
    conn: ConnDep,
    season: SeasonDep,
) -> dict[str, int]:
    a = _resolved_constructor(c1, season)
    b = _resolved_constructor(c2, season)
    try:
        return constructor_service.head_to_head(conn, a, b, season)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_CONSTRUCTOR_COMPARISON", "message": str(e)},
        ) from e


@router.get(
    "/{slug}/stats",
    summary="Full stats bundle for a constructor (one endpoint powers the detail page).",
)
async def constructor_stats(
    slug: str,
    conn: ConnDep,
    season: SeasonDep,
) -> dict:
    name = _resolved_constructor(slug, season)
    return constructor_service.get_stats(conn, name, season)


@router.get(
    "/{slug}/position/{position}",
    summary="Paginated championships where constructor finished at a specific position.",
)
async def constructor_position_championships(
    slug: str,
    position: int,
    conn: ConnDep,
    season: SeasonDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=500),
) -> dict:
    if position < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_POSITION", "message": "Position must be ≥ 1"},
        )
    name = _resolved_constructor(slug, season)
    return constructor_service.championships_at_position(
        conn, name, position, season, page, per_page
    )
