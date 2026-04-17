"""FastAPI app factory.

The new app runs alongside the old Flask app during parallel-run.
Flask serves the current site; FastAPI serves the rewrite on a different port
(default 8000) until cutover. Both read the same SQLite database.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.gzip import GZipMiddleware

from app.config import get_settings


log = logging.getLogger("f1")


def _configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    settings.instance_folder.mkdir(parents=True, exist_ok=True)
    log.info("Database at %s", settings.database_path)
    yield


def create_app() -> FastAPI:
    _configure_logging()
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="2.0.0",
        description="F1 championship scenario explorer.",
        docs_url="/api/docs",
        redoc_url=None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # Static assets (Vite outputs to app/static/dist/)
    if settings.static_folder.exists():
        app.mount(
            "/static",
            StaticFiles(directory=str(settings.static_folder)),
            name="static",
        )

    # Routers — wired up as each module is ported.
    from app.api import championships as api_championships
    from app.api import drivers as api_drivers
    from app.api import statistics as api_statistics
    from app.api import search as api_search
    from app.api import admin as api_admin
    from app.views import pages as view_pages
    from app.views import errors as view_errors

    app.include_router(api_championships.router, prefix="/api/championships", tags=["championships"])
    app.include_router(api_drivers.router, prefix="/api/drivers", tags=["drivers"])
    app.include_router(api_statistics.router, prefix="/api/statistics", tags=["statistics"])
    app.include_router(api_search.router, prefix="/api/search", tags=["search"])
    app.include_router(api_admin.router, prefix="/api/admin", tags=["admin"])
    app.include_router(view_pages.router, include_in_schema=False)

    view_errors.register(app)

    return app


app = create_app()
