"""CSV → numpy arrays.

The CSV layout supports race + sprint columns per weekend:
    Driver,1,2,2s,3,6,6s,7,7s,...
    VER,25,18,8,25,...
    NOR,18,25,6,18,...

- First column is the 3-letter driver code.
- Numeric headers (e.g. `1`, `6`) are race points for that round.
- Headers ending in `s` (e.g. `2s`, `6s`) are sprint points paired with the
  immediately-preceding race column.
- Round numbers may be non-contiguous (e.g. canceled rounds 4 and 5 in 2026).

Weekends stay coupled: a `championship` subset is over weekends, not sessions,
so the combinator consumes `race + sprint` per weekend as one score.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


class CSVLoadError(Exception):
    pass


@dataclass(frozen=True)
class LoadedSeason:
    drivers: np.ndarray  # shape (D,), 3-letter codes
    round_numbers: np.ndarray  # shape (W,), F1 round numbers for each weekend column
    race_scores: np.ndarray  # shape (D, W), race-only points
    sprint_scores: np.ndarray  # shape (D, W), 0 for non-sprint rounds

    @property
    def combined(self) -> np.ndarray:
        """Race + sprint per weekend — what the combinator consumes."""
        return self.race_scores + self.sprint_scores


def _parse_header(header: list[str]) -> list[tuple[int, str]]:
    """Parse header cells after the first (driver) column into (round, kind) pairs.

    `kind` is "race" or "sprint".
    """
    out: list[tuple[int, str]] = []
    last_round: int | None = None
    for raw in header:
        cell = raw.strip()
        if cell.endswith("s") or cell.endswith("S"):
            num = cell[:-1]
            kind = "sprint"
        else:
            num = cell
            kind = "race"
        try:
            n = int(num)
        except ValueError as e:
            raise CSVLoadError(f"Bad column header '{raw}': not a round number") from e
        if kind == "sprint":
            if last_round != n:
                raise CSVLoadError(
                    f"Sprint column '{raw}' must immediately follow race column for round {n}"
                )
        else:
            last_round = n
        out.append((n, kind))
    return out


def load(csv_path: Path) -> LoadedSeason:
    """Parse a season CSV into race/sprint matrices aligned by weekend column."""
    if not csv_path.exists():
        raise CSVLoadError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, dtype=str)
    if df.shape[1] < 2:
        raise CSVLoadError(f"{csv_path.name}: need a driver column + at least one round column")

    drivers = df.iloc[:, 0].astype(str).str.strip().str.upper().to_numpy()
    if len(drivers) != len(set(drivers)):
        raise CSVLoadError(f"{csv_path.name}: duplicate driver codes")

    header_cols = [str(c) for c in df.columns[1:]]
    parsed = _parse_header(header_cols)

    # Collect unique rounds in first-appearance order (also the CSV order).
    rounds: list[int] = []
    for round_num, _ in parsed:
        if not rounds or rounds[-1] != round_num:
            rounds.append(round_num)
    round_numbers = np.asarray(rounds, dtype=int)

    D = len(drivers)
    W = len(rounds)
    race = np.zeros((D, W), dtype=int)
    sprint = np.zeros((D, W), dtype=int)

    round_to_col = {r: i for i, r in enumerate(rounds)}
    raw = (
        df.iloc[:, 1:]
        .apply(pd.to_numeric, errors="coerce")
        .fillna(0)
        .astype(int)
        .to_numpy()
    )
    for src_idx, (round_num, kind) in enumerate(parsed):
        col = round_to_col[round_num]
        target = race if kind == "race" else sprint
        target[:, col] = raw[:, src_idx]

    return LoadedSeason(
        drivers=drivers,
        round_numbers=round_numbers,
        race_scores=race,
        sprint_scores=sprint,
    )


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
