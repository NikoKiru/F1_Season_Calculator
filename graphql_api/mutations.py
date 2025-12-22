"""
GraphQL Mutation definitions for F1 Season Calculator.
"""
import strawberry

from .types import ClearCacheResult
from .resolvers import clear_cache


@strawberry.type
class Mutation:
    """Root Mutation type for the F1 Season Calculator GraphQL API."""

    @strawberry.mutation(description="Clear all API caches")
    def clear_cache(self) -> ClearCacheResult:
        """
        Clear all API caches including:
        - Highest position cache
        - Head-to-head cache
        - Driver positions cache
        - Driver stats cache

        Useful after reprocessing data to ensure fresh results.
        """
        return clear_cache()
