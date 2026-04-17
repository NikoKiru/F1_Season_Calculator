"""Season CSV editing for incremental race additions.

Supports the sprint-column layout: race column `N` is optionally paired with a
sprint column `Ns` immediately after it. Both columns represent the same
weekend — selecting round N in a championship includes race + sprint points.

In-memory model:
    race[driver][round]   -> int points (race)
    sprint[driver][round] -> int points (sprint), keys only present for sprint rounds
"""
from __future__ import annotations

import csv
import re
from pathlib import Path


_DRIVER_RE = re.compile(r"^[A-Z]{3}$")


class ResultsParseError(ValueError):
    pass


def parse_results(raw: str) -> dict[str, int]:
    """Parse a "VER:25,NOR:18,LEC:15" string into {driver: points}."""
    out: dict[str, int] = {}
    for pair in (p.strip() for p in raw.split(",") if p.strip()):
        if ":" not in pair:
            raise ResultsParseError(f"Expected 'DRIVER:POINTS', got '{pair}'")
        code, points_raw = (x.strip() for x in pair.split(":", 1))
        code = code.upper()
        if not _DRIVER_RE.match(code):
            raise ResultsParseError(f"Invalid driver code '{code}' (need 3 letters)")
        try:
            points = int(points_raw)
        except ValueError as exc:
            raise ResultsParseError(f"Invalid points for {code}: '{points_raw}'") from exc
        out[code] = points
    if not out:
        raise ResultsParseError("No results provided")
    return out


def _parse_header_cell(cell: str) -> tuple[int, str]:
    cell = cell.strip()
    if cell.lower().endswith("s"):
        return int(cell[:-1]), "sprint"
    return int(cell), "race"


def load(
    csv_path: Path,
) -> tuple[list[str], dict[str, dict[int, int]], dict[str, dict[int, int]]]:
    """Return (drivers, race_data, sprint_data).

    `race_data[code][round]` = race points; `sprint_data[code][round]` = sprint points.
    Sprint data only has entries for rounds that include a sprint column.
    """
    if not csv_path.exists():
        return [], {}, {}

    drivers: list[str] = []
    race_data: dict[str, dict[int, int]] = {}
    sprint_data: dict[str, dict[int, int]] = {}

    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = [_parse_header_cell(h) for h in header[1:]]
        for row in reader:
            if not row:
                continue
            code = row[0].strip().upper()
            drivers.append(code)
            race_data[code] = {}
            sprint_data[code] = {}
            for i, (round_num, kind) in enumerate(cols):
                col = i + 1
                if col >= len(row):
                    continue
                value = row[col].strip()
                if not value:
                    continue
                try:
                    points = int(value)
                except ValueError:
                    points = 0
                if kind == "sprint":
                    sprint_data[code][round_num] = points
                else:
                    race_data[code][round_num] = points
    return drivers, race_data, sprint_data


def save(
    csv_path: Path,
    drivers: list[str],
    race_data: dict[str, dict[int, int]],
    sprint_data: dict[str, dict[int, int]],
) -> None:
    """Write CSV with race + sprint columns. Columns are sorted by round number;
    sprint rounds emit `N` then `Ns` pairs."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Union of all rounds touched across race and sprint data.
    rounds: set[int] = set()
    for d in race_data.values():
        rounds.update(d.keys())
    # Only emit sprint columns for rounds that actually have any sprint data.
    sprint_rounds: set[int] = set()
    for d in sprint_data.values():
        sprint_rounds.update(d.keys())
    rounds.update(sprint_rounds)

    ordered = sorted(rounds)
    header = ["Driver"]
    for r in ordered:
        header.append(str(r))
        if r in sprint_rounds:
            header.append(f"{r}s")

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for code in drivers:
            row: list[str] = [code]
            rdata = race_data.get(code, {})
            sdata = sprint_data.get(code, {})
            for r in ordered:
                row.append(str(rdata.get(r, 0)))
                if r in sprint_rounds:
                    row.append(str(sdata.get(r, 0)))
            w.writerow(row)


def apply_race(
    race_data: dict[str, dict[int, int]],
    sprint_data: dict[str, dict[int, int]],
    drivers: list[str],
    round_num: int,
    race_results: dict[str, int],
    sprint_results: dict[str, int] | None = None,
) -> list[str]:
    """Splice new results into the in-memory model. Returns the updated driver list."""
    for code in race_results:
        if code not in race_data:
            race_data[code] = {}
            sprint_data.setdefault(code, {})
            drivers.append(code)
    if sprint_results:
        for code in sprint_results:
            if code not in race_data:
                race_data[code] = {}
                sprint_data.setdefault(code, {})
                drivers.append(code)

    for code, points in race_results.items():
        race_data[code][round_num] = points
    # Zero-fill missing drivers for this round in the race column.
    for code in drivers:
        race_data.setdefault(code, {}).setdefault(round_num, 0)

    if sprint_results:
        for code, points in sprint_results.items():
            sprint_data[code][round_num] = points
        for code in drivers:
            sprint_data.setdefault(code, {}).setdefault(round_num, 0)
    return drivers
