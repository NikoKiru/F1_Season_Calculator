"""
GraphQL Query definitions for F1 Season Calculator.
"""
import strawberry
from typing import List, Optional

from .types import (
    Driver, Championship, PaginatedChampionships, ChampionshipWin,
    HighestPositionResult, HeadToHeadResult, MinRacesToWinResult,
    DriverPositionCount, ChampionshipWinProbability, DriverStats,
    FindChampionshipResult
)
from .resolvers import (
    get_all_drivers, get_driver_by_code, get_paginated_championships,
    get_championship_by_id, get_championship_wins, get_highest_positions,
    get_head_to_head, get_min_races_to_win, get_driver_positions,
    get_championship_win_probability, get_driver_stats,
    find_championship_by_rounds
)


@strawberry.type
class Query:
    """Root Query type for the F1 Season Calculator GraphQL API."""

    @strawberry.field(description="Get all F1 drivers")
    def drivers(self) -> List[Driver]:
        """Get all drivers with their information."""
        return get_all_drivers()

    @strawberry.field(description="Get a specific driver by code")
    def driver(self, code: str) -> Optional[Driver]:
        """Get a specific driver by their abbreviation code (e.g., VER, NOR, HAM)."""
        return get_driver_by_code(code)

    @strawberry.field(description="Get paginated list of championships")
    def championships(
        self,
        page: int = 1,
        per_page: int = 100
    ) -> PaginatedChampionships:
        """
        Fetch paginated list of all championship scenarios.

        Args:
            page: The page number to retrieve (default: 1)
            per_page: Number of results per page (default: 100)
        """
        return get_paginated_championships(page, per_page)

    @strawberry.field(description="Get a specific championship by ID")
    def championship(
        self,
        id: int,
        include_round_points: bool = True
    ) -> Optional[Championship]:
        """
        Fetch a specific championship scenario by its unique ID.

        Args:
            id: The unique championship ID
            include_round_points: Whether to include detailed round-by-round points
        """
        return get_championship_by_id(id, include_round_points)

    @strawberry.field(description="Get championship wins for all drivers")
    def championship_wins(self) -> List[ChampionshipWin]:
        """Get the total number of championship wins for each driver."""
        return get_championship_wins()

    @strawberry.field(description="Get highest championship position for each driver")
    def highest_positions(self, refresh: bool = False) -> List[HighestPositionResult]:
        """
        Get the best final championship ranking achieved by each driver.

        Args:
            refresh: Set to true to bypass cache and recalculate
        """
        return get_highest_positions(refresh)

    @strawberry.field(description="Head-to-head comparison between two drivers")
    def head_to_head(self, driver1: str, driver2: str) -> HeadToHeadResult:
        """
        Compare two drivers to see who finished ahead more often.

        Args:
            driver1: First driver abbreviation (e.g., VER)
            driver2: Second driver abbreviation (e.g., NOR)

        Raises:
            GraphQL error if comparing driver to themselves or invalid abbreviation
        """
        try:
            return get_head_to_head(driver1, driver2)
        except ValueError as e:
            raise strawberry.exceptions.GraphQLError(str(e))

    @strawberry.field(description="Minimum races needed for each driver to win")
    def min_races_to_win(self) -> List[MinRacesToWinResult]:
        """Get the minimum number of races each driver needed to win a championship."""
        return get_min_races_to_win()

    @strawberry.field(description="Count driver finishes in a specific position")
    def driver_positions(self, position: int) -> List[DriverPositionCount]:
        """
        Count how many times each driver finished in a given position.

        Args:
            position: The championship position to count (must be >= 1)
        """
        try:
            return get_driver_positions(position)
        except ValueError as e:
            raise strawberry.exceptions.GraphQLError(str(e))

    @strawberry.field(description="Championship win probability by season length")
    def championship_win_probability(self) -> ChampionshipWinProbability:
        """
        Get win probability matrix showing each driver's chance of winning
        based on season length.
        """
        return get_championship_win_probability()

    @strawberry.field(description="Comprehensive statistics for a driver")
    def driver_stats(self, driver_code: str) -> Optional[DriverStats]:
        """
        Get aggregated statistics for a specific driver including:
        - Total wins and win percentage
        - Highest position achieved
        - Head-to-head records against all opponents
        - Position distribution
        - Win probability by season length

        Args:
            driver_code: The driver abbreviation (e.g., VER, NOR, HAM)
        """
        return get_driver_stats(driver_code)

    @strawberry.field(description="Find a championship by round numbers")
    def find_championship(self, rounds: List[int]) -> FindChampionshipResult:
        """
        Find an existing championship scenario from a list of round numbers.

        Args:
            rounds: List of round numbers (1-24 for 2025 season)
        """
        return find_championship_by_rounds(rounds)
