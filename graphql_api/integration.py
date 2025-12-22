"""
Flask integration for Strawberry GraphQL.
"""
from flask import Blueprint
from strawberry.flask.views import GraphQLView

from .schema import schema

# Create Blueprint for GraphQL
graphql_bp = Blueprint('graphql', __name__, url_prefix='/graphql')

# Add GraphQL view with GraphiQL playground enabled
graphql_bp.add_url_rule(
    '',
    view_func=GraphQLView.as_view('graphql', schema=schema)
)
