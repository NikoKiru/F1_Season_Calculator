from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import ConnDep, SeasonDep


router = APIRouter()


def _parse_rounds(raw: str) -> list[int]:
    """Validate & normalize 'rounds' query string (e.g. '1,2,3')."""
    if not raw:
        raise ValueError("rounds is required")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    rounds: list[int] = []
    for p in parts:
        try:
            n = int(p)
        except ValueError as e:
            raise ValueError(f"Invalid round '{p}': not an integer") from e
        if n < 1 or n > 24:
            raise ValueError(f"Round {n} out of range (1–24)")
        rounds.append(n)
    if len(rounds) != len(set(rounds)):
        raise ValueError("Duplicate rounds are not allowed")
    return sorted(rounds)


@router.get(
    "/championship",
    summary="Find an existing championship by its exact round combination.",
)
async def find_championship(
    conn: ConnDep,
    season: SeasonDep,
    rounds: Annotated[str, Query(description="Comma-separated round numbers (1–24)")],
) -> dict:
    from app.services import championship_service

    try:
        round_list = _parse_rounds(rounds)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_ROUNDS", "message": str(e)},
        ) from e

    cid = championship_service.find_by_rounds(conn, round_list, season)
    if cid is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "CHAMPIONSHIP_NOT_FOUND",
                "message": "No championship exists for this round combination",
                "rounds": round_list,
                "season": season,
            },
        )
    return {"championship_id": cid, "url": f"/championship/{cid}"}
