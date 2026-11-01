"""One cache abstraction for the whole app.

Wraps cachetools.TTLCache so every endpoint uses the same keys-and-TTL pattern.
Rebuilds and syncs run in other processes, so each access compares the files
cached results come from and drops everything when one of them has changed.
"""
from collections.abc import Callable
from pathlib import Path
from threading import RLock
from typing import Any, TypeVar

from cachetools import TTLCache

from app.config import get_settings

T = TypeVar("T")

_lock = RLock()
_cache: TTLCache[str, Any] | None = None
_data_stamp: tuple[tuple[int, int], ...] | None = None


def _file_stamp(path: Path) -> tuple[int, int]:
    try:
        stat = path.stat()
    except OSError:
        return (0, 0)
    return (stat.st_mtime_ns, stat.st_size)


def _current_data_stamp() -> tuple[tuple[int, int], ...]:
    # The WAL counts because a rebuild's last commits stay there, not in the
    # database file, for as long as the server's pool holds connections open.
    s = get_settings()
    database = s.database_path
    wal = database.with_name(f"{database.name}-wal")
    seasons = sorted(s.seasons_folder.glob("*.json"))
    return tuple(_file_stamp(path) for path in (database, wal, *seasons))


def _cache_instance() -> TTLCache[str, Any]:
    global _cache, _data_stamp
    if _cache is None:
        s = get_settings()
        _cache = TTLCache(maxsize=s.cache_maxsize, ttl=s.cache_ttl_seconds)
    stamp = _current_data_stamp()
    if stamp != _data_stamp:
        _cache.clear()
        _data_stamp = stamp
    return _cache


def get_or_compute(key: str, compute: Callable[[], T]) -> T:
    with _lock:
        cache = _cache_instance()
        if key in cache:
            return cache[key]  # type: ignore[no-any-return]
        stamp = _data_stamp
    value = compute()
    with _lock:
        cache = _cache_instance()
        # Data that changed mid-compute can leave a half-old result: use it, don't keep it.
        if _data_stamp == stamp:
            cache[key] = value
    return value


def clear() -> None:
    with _lock:
        _cache_instance().clear()


# --- canonical key builders -----------------------------------------------

def key_championship(cid: int) -> str:
    return f"championship:{cid}"


def key_all_wins(season: int) -> str:
    return f"all-wins:{season}"


def key_highest_position(season: int) -> str:
    return f"highest-position:{season}"


def key_min_races_to_win(season: int) -> str:
    return f"min-races:{season}"


def key_driver_stats(code: str, season: int) -> str:
    return f"driver-stats:{season}:{code}"


def key_head_to_head(d1: str, d2: str, season: int) -> str:
    a, b = sorted((d1, d2))
    return f"h2h:{season}:{a}:{b}"


def key_driver_positions(position: int, season: int) -> str:
    return f"driver-positions:{season}:{position}"


def key_win_probability(season: int) -> str:
    return f"win-probability:{season}"


def key_notable_scenarios(season: int) -> str:
    return f"notable-scenarios:{season}"


def key_search_rounds(rounds_csv: str, season: int) -> str:
    return f"search:{season}:{rounds_csv}"
