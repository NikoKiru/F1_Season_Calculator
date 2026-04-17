"""Create the SQLite file + schema from scratch (or reuse an existing one)."""
from __future__ import annotations

from pathlib import Path

from app.data.engine import get_engine, dispose_engine
from app.data.schema import init_schema


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = get_engine(db_path)
    with engine.begin() as conn:
        init_schema(conn)


def reset(db_path: Path) -> None:
    """Delete the DB file (and WAL artifacts) then recreate with fresh schema."""
    dispose_engine(db_path)
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()
    ensure_schema(db_path)
