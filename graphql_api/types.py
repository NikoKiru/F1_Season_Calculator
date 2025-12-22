"""
Strawberry GraphQL type definitions for F1 Season Calculator.
"""
import strawberry
from typing import List, Optional


@strawberry.type
class Driver:
    """Represents an F1 driver."""
    code: str
    name: str
    team: str
    number: int
    flag: str
    color: str


@strawberry.type
class DriverPointEntry:
    """Driver points entry in championship standings."""
    driver_code: str
    points: int
    driver_name: str


@strawberry.type
class RoundPointsData:
    """Points data for each round in a championship."""
    driver_code: str
    round_points: List[int]
    total_points: int


@strawberry.type
class Championship:
    """Represents a championship scenario."""
    championship_id: int
    num_races: int
    rounds: List[int]
    round_names: List[str]
    standings: List[str]
    winner: str
    points: List[int]
    driver_points: List[DriverPointEntry]
    round_points_data: Optional[List[RoundPointsData]] = None


@strawberry.type
class PaginatedChampionships:
    """Paginated list of championships."""
    total_results: int
    total_pages: int
    current_page: int
    per_page: int
    results: List[Championship]


@strawberry.type
class ChampionshipWin:
    """Championship wins for a driver."""
    driver_code: str
    wins: int


@strawberry.type
class HighestPositionResult:
    """Highest championship position achieved by a driver."""
    driver: str
    position: int
    championship_ids: List[int]


@strawberry.type
class HeadToHeadResult:
    """Head-to-head comparison between two drivers."""
    driver1: str
    driver1_wins: int
    driver2: str
    driver2_wins: int


@strawberry.type
class MinRacesToWinResult:
    """Minimum races needed for a driver to win a championship."""
    driver_code: str
    min_races: int


@strawberry.type
class DriverPositionCount:
    """Count of times a driver finished in a specific position."""
    driver: str
    count: int
    percentage: float


@strawberry.type
class DriverProbabilityData:
    """Win probability data for a driver across season lengths."""
    driver: str
    total_titles: int
    wins_per_length: List[int]
    percentages: List[float]


@strawberry.type
class ChampionshipWinProbability:
    """Championship win probability matrix."""
    season_lengths: List[int]
    possible_seasons: List[int]
    drivers_data: List[DriverProbabilityData]


@strawberry.type
class PositionCount:
    """Position distribution entry."""
    position: int
    count: int


@strawberry.type
class HeadToHeadRecord:
    """Head-to-head record against an opponent."""
    opponent_code: str
    wins: int
    losses: int


@strawberry.type
class WinProbabilityByLength:
    """Win probability for a specific season length."""
    season_length: int
    percentage: float


@strawberry.type
class DriverStats:
    """Comprehensive statistics for a driver."""
    driver_code: str
    driver_name: str
    driver_info: Driver
    total_wins: int
    total_championships: int
    win_percentage: float
    highest_position: int
    highest_position_championship_id: Optional[int]
    min_races_to_win: Optional[int]
    position_distribution: List[PositionCount]
    head_to_head: List[HeadToHeadRecord]
    win_probability_by_length: List[WinProbabilityByLength]


@strawberry.type
class FindChampionshipResult:
    """Result of finding a championship by rounds."""
    url: Optional[str] = None
    error: Optional[str] = None


@strawberry.type
class ClearCacheResult:
    """Result of clearing the cache."""
    success: bool
    message: str
