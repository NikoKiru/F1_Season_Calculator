from typing import Dict, TypedDict


class DriverInfo(TypedDict):
    """Type definition for driver information."""
    name: str
    team: str
    number: int
    flag: str
    color: str


# Official team colors from OpenF1 API (2025 season)
TEAM_COLORS: Dict[str, str] = {
    "McLaren": "#F47600",
    "Red Bull Racing": "#4781D7",
    "Mercedes": "#00D7B6",
    "Ferrari": "#ED1131",
    "Aston Martin": "#229971",
    "Williams": "#1868DB",
    "Racing Bulls": "#6C98FF",
    "Sauber": "#01C00E",
    "Haas": "#9C9FA2",
    "Alpine": "#00A1E8",
}

DRIVERS: Dict[str, Dict[str, str | int]] = {
    "PIA": {"name": "Oscar Piastri", "team": "McLaren", "number": 81, "flag": "🇦🇺"},
    "NOR": {"name": "Lando Norris", "team": "McLaren", "number": 4, "flag": "🇬🇧"},
    "VER": {"name": "Max Verstappen", "team": "Red Bull Racing", "number": 1, "flag": "🇳🇱"},
    "RUS": {"name": "George Russell", "team": "Mercedes", "number": 63, "flag": "🇬🇧"},
    "LEC": {"name": "Charles Leclerc", "team": "Ferrari", "number": 16, "flag": "🇲🇨"},
    "HAM": {"name": "Lewis Hamilton", "team": "Ferrari", "number": 44, "flag": "🇬🇧"},
    "ANT": {"name": "Andrea Kimi Antonelli", "team": "Mercedes", "number": 12, "flag": "🇮🇹"},
    "ALB": {"name": "Alex Albon", "team": "Williams", "number": 23, "flag": "🇹🇭"},
    "HAD": {"name": "Isack Hadjar", "team": "Racing Bulls", "number": 37, "flag": "🇫🇷"},
    "HUL": {"name": "Nico Hülkenberg", "team": "Sauber", "number": 27, "flag": "🇩🇪"},
    "STR": {"name": "Lance Stroll", "team": "Aston Martin", "number": 18, "flag": "🇨🇦"},
    "SAI": {"name": "Carlos Sainz", "team": "Williams", "number": 55, "flag": "🇪🇸"},
    "LAW": {"name": "Liam Lawson", "team": "Racing Bulls", "number": 30, "flag": "🇳🇿"},
    "ALO": {"name": "Fernando Alonso", "team": "Aston Martin", "number": 14, "flag": "🇪🇸"},
    "OCO": {"name": "Esteban Ocon", "team": "Haas", "number": 31, "flag": "🇫🇷"},
    "GAS": {"name": "Pierre Gasly", "team": "Alpine", "number": 10, "flag": "🇫🇷"},
    "TSU": {"name": "Yuki Tsunoda", "team": "Red Bull Racing", "number": 22, "flag": "🇯🇵"},
    "BOR": {"name": "Gabriel Bortoleto", "team": "Sauber", "number": 8, "flag": "🇧🇷"},
    "BEA": {"name": "Oliver Bearman", "team": "Haas", "number": 50, "flag": "🇬🇧"},
    "COL": {"name": "Franco Colapinto", "team": "Alpine", "number": 43, "flag": "🇦🇷"},
}

# Add color to each driver based on their team
for driver_code, driver_data in DRIVERS.items():
    driver_data["color"] = TEAM_COLORS.get(driver_data["team"], "#FFFFFF")

DRIVER_NAMES: Dict[str, str] = {k: v['name'] for k, v in DRIVERS.items()}

ROUND_NAMES_2025: Dict[int, str] = {
    1: "AUS",
    2: "CHN",
    3: "JPN",
    4: "BHR",
    5: "SAU",
    6: "MIA",
    7: "EMI",
    8: "MON",
    9: "ESP",
    10: "CAN",
    11: "AUT",
    12: "GBR",
    13: "BEL",
    14: "HUN",
    15: "NED",
    16: "ITA",
    17: "AZE",
    18: "SIN",
    19: "USA",
    20: "MXC",
    21: "SAP",
    22: "LVG",
    23: "QAT",
    24: "ABU",
}
