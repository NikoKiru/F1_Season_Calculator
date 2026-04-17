from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool


_engines: dict[Path, Engine] = {}


def get_engine(db_path: Path) -> Engine:
    """Return a cached pooled engine for a SQLite file.

    Pool sizing + SQLite pragmas match the old project's tuned values so the
    perf profile carries over — see db.py:18-63 in the old code.
    """
    resolved = db_path.resolve()
    if resolved in _engines:
        return _engines[resolved]

    resolved.parent.mkdir(parents=True, exist_ok=True)

    engine = create_engine(
        f"sqlite:///{resolved}",
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=3600,
        future=True,
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, _):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA cache_size=-50000")
        cursor.execute("PRAGMA mmap_size=268435456")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    _engines[resolved] = engine
    return engine


def dispose_engine(db_path: Path) -> None:
    resolved = db_path.resolve()
    engine = _engines.pop(resolved, None)
    if engine is not None:
        engine.dispose()
