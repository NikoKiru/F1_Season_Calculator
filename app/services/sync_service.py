"""Pure season-sync logic — no I/O, fully unit-testable.

The `f1 sync` command wires these helpers to the Jolpica client and the
CSV/JSON files. Policy encoded here:

- Rounds already raced (present in the CSV) are historical facts: their labels
  are frozen and they survive even if the API drops them.
- Future rounds are forecasts: labels, additions, and removals follow the
  API schedule (handles mid-season cancellations and renumbering).
- `sprint_rounds` is the union of schedule sprints and sprints already raced.
- Count blobs (career/palmarès) only get a fresh `updated_at` when a value
  actually changed, so a no-op refresh produces a byte-identical file.
"""
from __future__ import annotations

from datetime import date

from app.services import circuit_codes


def _label_for(entry: dict) -> tuple[str, bool]:
    """Return (label, known) for a schedule entry."""
    known = circuit_codes.lookup(entry.get("circuit_id", ""))
    if known:
        return known, True
    return circuit_codes.fallback(entry.get("circuit_id", "")), False


def merge_schedule(
    raw: dict,
    schedule: list[dict],
    *,
    raced_rounds: set[int],
    raced_sprints: set[int],
) -> tuple[dict, list[str]]:
    """Merge the API schedule into a season JSON dict.

    Returns (new_raw, changes). `raw` is not mutated; an empty change list
    means the file does not need rewriting.
    """
    changes: list[str] = []
    old_rounds: dict[str, str] = dict(raw.get("rounds", {}))
    new_rounds: dict[str, str] = {}

    scheduled = {entry["round"]: entry for entry in schedule}

    for round_num, entry in scheduled.items():
        key = str(round_num)
        existing = old_rounds.get(key)
        if round_num in raced_rounds and existing:
            new_rounds[key] = existing  # frozen: history wins
            continue
        label, known = _label_for(entry)
        new_rounds[key] = label
        if not known:
            changes.append(
                f"round {round_num}: unknown circuit '{entry.get('circuit_id')}' — "
                f"labeled {label}, rename in seasons JSON if wrong"
            )
        if existing is None:
            changes.append(f"round {round_num}: added ({new_rounds[key]})")
        elif new_rounds[key] != existing:
            changes.append(f"round {round_num}: relabeled {existing} -> {new_rounds[key]}")

    for key, label in old_rounds.items():
        round_num = int(key)
        if round_num in scheduled:
            continue
        if round_num in raced_rounds:
            new_rounds[key] = label  # raced but missing from API: keep
        else:
            changes.append(f"round {round_num}: removed (dropped from schedule)")

    schedule_sprints = {e["round"] for e in schedule if e.get("has_sprint")}
    new_sprints = sorted(schedule_sprints | set(raced_sprints))
    old_sprints = sorted(int(r) for r in raw.get("sprint_rounds", []))
    if new_sprints != old_sprints:
        changes.append(f"sprint_rounds: {old_sprints} -> {new_sprints}")

    # Keys sorted numerically so the JSON diff stays readable.
    new_rounds = {k: new_rounds[k] for k in sorted(new_rounds, key=int)}
    if new_rounds == old_rounds and new_sprints == old_sprints:
        return raw, []

    merged = dict(raw)
    merged["rounds"] = new_rounds
    merged["sprint_rounds"] = new_sprints
    return merged, changes


def plan_missing_rounds(
    schedule: list[dict], csv_rounds: set[int], *, today: date
) -> list[int]:
    """Rounds whose race date has passed (or is today) but have no CSV column yet."""
    due: list[int] = []
    for entry in schedule:
        raw_date = entry.get("date") or ""
        try:
            race_date = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if race_date <= today and entry["round"] not in csv_rounds:
            due.append(entry["round"])
    return sorted(due)


def merge_counts(
    existing: dict | None, fetched: dict, now_iso: str
) -> tuple[dict, bool]:
    """Merge fetched counts over existing ones, preserving hand-curated keys.

    `updated_at` is only stamped when a fetched value differs — an unchanged
    record is returned as-is so callers can skip the file write entirely.
    """
    base = dict(existing or {})
    changed = any(base.get(k) != v for k, v in fetched.items())
    if not changed and existing is not None:
        return base, False
    merged = {**base, **fetched, "updated_at": now_iso}
    return merged, True


def roster_gaps(csv_drivers: list[str] | tuple[str, ...], raw: dict) -> list[str]:
    """Driver codes present in results but missing from the season JSON roster."""
    known = set(raw.get("drivers", {}))
    return sorted({code for code in csv_drivers if code and code not in known})
