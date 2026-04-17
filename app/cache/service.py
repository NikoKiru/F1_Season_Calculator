"""One cache abstraction for the whole app.

Wraps cachetools.TTLCache so every endpoint uses the same keys-and-TTL pattern.
The old project sprinkled flask_caching.memoize() calls throughout api.py with
inconsistent key formats — this collapses that into named helpers.
"""
from collections.abc import Callable
from threading import RLock
from typing import Any, TypeVar

from cachetools import TTLCache

from app.config import get_settings


T = TypeVar("T")

_lock = RLock()
_cache: TTLCache[str, Any] | None = None


def _cache_instance() -> TTLCache[str, Any]:
    global _cache
    if _cache is None:
        s = get_settings()
        _cache = TTLCache(maxsize=s.cache_maxsize, ttl=s.cache_ttl_seconds)
    return _cache


def get(key: str) -> Any | None:
    with _lock:
        return _cache_instance().get(key)


def set(key: str, value: Any) -> None:
    with _lock:
        _cache_instance()[key] = value


def get_or_compute(key: str, compute: Callable[[], T]) -> T:
    with _lock:
        cache = _cache_instance()
        if key in cache:
            return cache[key]  # type: ignore[no-any-return]
    value = compute()
    with _lock:
        _cache_instance()[key] = value
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


def key_search_rounds(rounds_csv: str, season: int) -> str:
    return f"search:{season}:{rounds_csv}"
