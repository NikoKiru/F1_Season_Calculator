"""Circuit-id → 3-letter round label, matching data/seasons/{YYYY}.json conventions.

The map covers every circuit on the calendar since 2020 plus likely returns.
Unknown circuits fall back to the first three letters of the circuit id —
callers should surface a warning so the label can be hand-curated.

Note: `catalunya` maps to BAR (not ESP) because from 2026 the Spanish GP label
belongs to Madrid (`madring`). Older seasons are already curated on disk and
are never relabeled retroactively (see sync_service.merge_schedule).
"""
from __future__ import annotations

_CIRCUIT_TO_CODE = {
    "albert_park": "AUS",
    "shanghai": "CHN",
    "suzuka": "JPN",
    "bahrain": "BHR",
    "jeddah": "SAU",
    "miami": "MIA",
    "imola": "EMI",
    "monaco": "MON",
    "catalunya": "BAR",
    "madring": "ESP",
    "villeneuve": "CAN",
    "red_bull_ring": "AUT",
    "silverstone": "GBR",
    "spa": "BEL",
    "hungaroring": "HUN",
    "zandvoort": "NED",
    "monza": "ITA",
    "baku": "AZE",
    "marina_bay": "SIN",
    "americas": "USA",
    "rodriguez": "MXC",
    "interlagos": "SAP",
    "vegas": "LVG",
    "losail": "QAT",
    "yas_marina": "ABU",
    # Recent-past circuits that could plausibly return.
    "portimao": "POR",
    "istanbul": "TUR",
    "sochi": "RUS",
    "paul_ricard": "FRA",
    "nurburgring": "EIF",
    "mugello": "TUS",
    "hockenheimring": "GER",
    "sepang": "MAL",
}


# Round label → host-country ISO 3166-1 alpha-2, matching
# app/static/flags/{iso}.svg. Street/round labels that aren't country codes
# (MIA, EMI, BAR, SAP, …) still resolve to the country that hosts them.
_LABEL_TO_ISO = {
    "AUS": "au",
    "CHN": "cn",
    "JPN": "jp",
    "BHR": "bh",
    "SAU": "sa",
    "MIA": "us",
    "EMI": "it",
    "MON": "mc",
    "BAR": "es",
    "ESP": "es",
    "CAN": "ca",
    "AUT": "at",
    "GBR": "gb",
    "BEL": "be",
    "HUN": "hu",
    "NED": "nl",
    "ITA": "it",
    "AZE": "az",
    "SIN": "sg",
    "USA": "us",
    "MXC": "mx",
    "SAP": "br",
    "LVG": "us",
    "QAT": "qa",
    "ABU": "ae",
    "POR": "pt",
    "TUR": "tr",
    "RUS": "ru",
    "FRA": "fr",
    "EIF": "de",
    "TUS": "it",
    "GER": "de",
    "MAL": "my",
}


def lookup(circuit_id: str) -> str | None:
    """Return the curated label for a circuit id, or None if unknown."""
    return _CIRCUIT_TO_CODE.get(circuit_id)


def country_for(label: str | None) -> str | None:
    """ISO alpha-2 host country for a round label, or None if unknown."""
    if not label:
        return None
    return _LABEL_TO_ISO.get(label.strip().upper())


def fallback(circuit_id: str) -> str:
    """Derive a label from the circuit id: first three alpha chars, uppercased,
    padded with X for degenerate ids."""
    letters = [ch for ch in circuit_id.upper() if ch.isalpha()]
    return "".join(letters[:3]).ljust(3, "X")
