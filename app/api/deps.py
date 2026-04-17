"""Shared FastAPI dependencies: season resolution + driver-code validation."""
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from sqlalchemy import Connection

from app.data.session import get_db
from app.services import season_service


def current_season(
    season: Annotated[int | None, Query(description="Season year; defaults to the latest configured.")] = None,
) -> int:
    return season if season is not None else season_service.default_season()


SeasonDep = Annotated[int, Depends(current_season)]
ConnDep = Annotated[Connection, Depends(get_db)]


def validated_driver(code: str, season: int) -> str:
    try:
        return season_service.resolve_driver_code(code, season)
    except ValueError as e:
        # Same shape for both length and roster errors, but different status codes
        if "3 letters" in str(e):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_DRIVER_CODE", "message": str(e)},
            ) from e
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "DRIVER_NOT_FOUND", "message": str(e)},
        ) from e
