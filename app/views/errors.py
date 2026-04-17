"""HTTP error handlers — HTML for browser requests, JSON for /api/*."""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.services import season_service
from app.templating import render


_TITLES = {
    400: ("Bad request", "The request couldn't be understood."),
    404: ("Not found", "We couldn't find what you were looking for."),
    405: ("Method not allowed", "That URL doesn't support this action."),
    500: ("Server error", "Something went wrong on our end."),
}


def _wants_json(request: Request) -> bool:
    return request.url.path.startswith("/api/") or "application/json" in request.headers.get(
        "accept", ""
    )


def register(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException):
        status = exc.status_code
        if _wants_json(request):
            return JSONResponse(
                status_code=status,
                content={"detail": exc.detail if exc.detail else _TITLES.get(status, ("", ""))[0]},
            )
        title, message = _TITLES.get(status, ("Error", "Unexpected error."))
        season = season_service.default_season()
        return render(
            request,
            "errors/error.html",
            {
                "status": status,
                "title": title,
                "message": message,
                "current_season": season,
                "seasons": list(season_service.available_seasons()),
            },
            status_code=status,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={"detail": {"code": "VALIDATION_ERROR", "errors": exc.errors()}},
        )

    @app.exception_handler(500)
    async def _server_error(request: Request, exc):  # noqa: ARG001
        if _wants_json(request):
            return JSONResponse(status_code=500, content={"detail": "server_error"})
        season = season_service.default_season()
        return render(
            request,
            "errors/error.html",
            {
                "status": 500,
                "title": "Server error",
                "message": "Something went wrong on our end.",
                "current_season": season,
                "seasons": list(season_service.available_seasons()),
            },
            status_code=500,
        )
