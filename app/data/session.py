from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Connection

from app.config import get_settings
from app.data.engine import get_engine


@contextmanager
def db_connection() -> Iterator[Connection]:
    """Context-managed connection for CLI / pipeline / tests."""
    engine = get_engine(get_settings().database_path)
    with engine.connect() as conn:
        yield conn


def get_db() -> Iterator[Connection]:
    """FastAPI dependency — yields a pooled connection per request."""
    engine = get_engine(get_settings().database_path)
    with engine.connect() as conn:
        yield conn
