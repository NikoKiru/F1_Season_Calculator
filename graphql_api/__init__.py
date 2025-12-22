"""
GraphQL module for F1 Season Calculator.

This module provides a GraphQL API alongside the existing REST API.
The GraphQL endpoint is available at /graphql with an interactive
GraphiQL playground.
"""
from .integration import graphql_bp
from .schema import schema

__all__ = ['graphql_bp', 'schema']
