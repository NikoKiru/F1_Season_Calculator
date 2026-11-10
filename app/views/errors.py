"""HTTP error handlers — HTML for browser requests, JSON for /api/*."""
from __future__ import annotations

from http import HTTPStatus

from fastapi import FastAPI, Request
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


def _reason(status: int, detail: object) -> str | None:
    """What the raising code said went wrong, when it said more than the status."""
    if isinstance(detail, dict):
        detail = detail.get("message")
    if not isinstance(detail, str) or not detail:
        return None
    try:
        if detail == HTTPStatus(status).phrase:
            return None
    except ValueError:
        pass
    return detail


def _error_page(request: Request, status: int, reason: str | None = None):
    title, message = _TITLES.get(status, ("Error", "Unexpected error."))
    return render(
        request,
        "errors/error.html",
        {
            "status": status,
            "title": title,
            "message": reason or message,
            "current_season": season_service.default_season(),
            "seasons": list(season_service.available_seasons()),
        },
        status_code=status,
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
        return _error_page(request, status, _reason(status, exc.detail))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError):
        if _wants_json(request):
            return JSONResponse(
                status_code=422,
                content={"detail": {"code": "VALIDATION_ERROR", "errors": exc.errors()}},
            )
        # A page whose path doesn't parse names nothing; a bad query string is
        # a request for a real page that can't be met as asked.
        errors = exc.errors()
        if any(error["loc"][0] == "path" for error in errors):
            return _error_page(request, 404)
        reason = "; ".join(f"{error['loc'][-1]}: {error['msg']}" for error in errors)
        return _error_page(request, 400, f"Check the address. {reason}.")

    @app.exception_handler(500)
    async def _server_error(request: Request, exc):
        if _wants_json(request):
            return JSONResponse(status_code=500, content={"detail": "server_error"})
        return _error_page(request, 500)
