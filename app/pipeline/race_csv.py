"""Season CSV editing for incremental race additions.

The `add-race` CLI lets a user append one race to a season without editing
the CSV by hand. This module is the minimum needed to support that flow:
read the existing CSV, splice in a new column, write it back. Actual
re-processing is handled by `writer.process_season`.
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


def load(csv_path: Path) -> tuple[list[str], dict[str, dict[int, int]]]:
    """Return (ordered driver list, {driver: {round: points}}) from an existing season CSV."""
    if not csv_path.exists():
        return [], {}

    drivers: list[str] = []
    data: dict[str, dict[int, int]] = {}
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        rounds = [int(h) for h in header[1:]]
        for row in reader:
            if not row:
                continue
            code = row[0].strip().upper()
            drivers.append(code)
            data[code] = {}
            for i, round_num in enumerate(rounds):
                col = i + 1
                if col < len(row) and row[col].strip():
                    try:
                        data[code][round_num] = int(row[col])
                    except ValueError:
                        data[code][round_num] = 0
    return drivers, data


def save(
    csv_path: Path,
    drivers: list[str],
    data: dict[str, dict[int, int]],
    max_round: int,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Driver", *(str(r) for r in range(1, max_round + 1))])
        for code in drivers:
            row = [code]
            rounds = data.get(code, {})
            row.extend(str(rounds.get(r, 0)) for r in range(1, max_round + 1))
            writer.writerow(row)


def apply_race(
    data: dict[str, dict[int, int]],
    drivers: list[str],
    round_num: int,
    results: dict[str, int],
) -> list[str]:
    """Splice new race results into the in-memory CSV model. Returns the updated driver list."""
    for code in results:
        if code not in data:
            data[code] = {}
            drivers.append(code)
    for code, points in results.items():
        data[code][round_num] = points
    # Zero-fill missing rounds for every driver
    for code in drivers:
        data.setdefault(code, {}).setdefault(round_num, 0)
    return drivers
