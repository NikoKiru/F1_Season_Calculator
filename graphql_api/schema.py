"""
Strawberry GraphQL schema for F1 Season Calculator.
"""
import strawberry

from .queries import Query
from .mutations import Mutation

# Create the GraphQL schema
schema = strawberry.Schema(query=Query, mutation=Mutation)
