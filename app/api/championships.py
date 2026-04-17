from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ConnDep, SeasonDep
from app.services import championship_service


router = APIRouter()


@router.get(
    "",
    summary="Paginated list of championships for a season.",
)
async def list_championships(
    conn: ConnDep,
    season: SeasonDep,
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=1000),
) -> dict:
    return championship_service.get_page(conn, season, page, per_page)


@router.get(
    "/wins",
    summary="Championship wins per driver for a season.",
    response_model=dict[str, int],
)
async def wins(conn: ConnDep, season: SeasonDep) -> dict[str, int]:
    return championship_service.all_wins(conn, season)


@router.get(
    "/min-races-to-win",
    summary="Fewest races at which each driver has ever won.",
    response_model=dict[str, int],
)
async def min_races(conn: ConnDep, season: SeasonDep) -> dict[str, int]:
    return championship_service.min_races_to_win(conn, season)


@router.get(
    "/{championship_id}",
    summary="Single championship scenario by id.",
)
async def get_championship(championship_id: int, conn: ConnDep) -> dict:
    result = championship_service.get_by_id(conn, championship_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "CHAMPIONSHIP_NOT_FOUND", "message": "Championship not found"},
        )
    return result
