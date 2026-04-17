"""CSV → numpy arrays.

The CSV layout (inherited from the original project) is:
    Driver,1,2,3,...N
    VER,25,18,25,...
    NOR,18,25,18,...

First column is the 3-letter driver code; the remaining columns are points
per round. We tolerate blank cells and trailing whitespace in driver codes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


class CSVLoadError(Exception):
    pass


def load(csv_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """Return (drivers, scores) where `drivers` is shape (D,) and `scores` is (D, N)."""
    if not csv_path.exists():
        raise CSVLoadError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if df.shape[1] < 2:
        raise CSVLoadError(f"{csv_path.name}: need a driver column + at least one round column")

    drivers = df.iloc[:, 0].astype(str).str.strip().str.upper().to_numpy()
    scores = (
        df.iloc[:, 1:]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
        .to_numpy()
    )

    if len(drivers) != len(set(drivers)):
        raise CSVLoadError(f"{csv_path.name}: duplicate driver codes")

    return drivers, scores


def resolve_csv(data_folder: Path, season: int) -> Path:
    """Resolve the season CSV, preferring season-specific, falling back to generic."""
    season_specific = data_folder / f"championships_{season}.csv"
    generic = data_folder / "championships.csv"
    if season_specific.exists():
        return season_specific
    if generic.exists():
        return generic
    raise CSVLoadError(
        f"No CSV found. Expected {season_specific.name} or {generic.name} in {data_folder}"
    )
