"""
Championship module for F1 Season Calculator.

This module provides the core functionality for analyzing F1 championship scenarios.
"""

# Import blueprints and init functions for external use
from .api import bp as api_bp
from .views import bp as views_bp
from .errors import errors_bp, init_app as init_errors
from .commands import init_app as init_commands

# Import commonly used models for convenience
from .models import DRIVERS, DRIVER_NAMES, ROUND_NAMES_2025, TEAM_COLORS

__all__ = [
    # Blueprints
    'api_bp',
    'views_bp',
    'errors_bp',
    # Init functions
    'init_errors',
    'init_commands',
    # Models
    'DRIVERS',
    'DRIVER_NAMES',
    'ROUND_NAMES_2025',
    'TEAM_COLORS',
]
