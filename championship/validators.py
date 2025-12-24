"""
Input validation utilities for API endpoints.

Provides consistent validation and error messages across all endpoints.
"""
from typing import Tuple, Optional, List, Any

# Validation constants
MAX_PAGE_SIZE = 1000
MIN_PAGE = 1
MIN_PAGE_SIZE = 1
MAX_POSITION = 24  # Maximum number of drivers
MIN_POSITION = 1
MAX_ROUND = 24  # Maximum number of races in a season
MIN_ROUND = 1
DRIVER_CODE_LENGTH = 3


class ValidationError(Exception):
    """Exception raised for validation errors."""

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(self.message)


def validate_pagination(
    page: Any,
    per_page: Any,
    max_per_page: int = MAX_PAGE_SIZE
) -> Tuple[int, int]:
    """
    Validate pagination parameters.

    Args:
        page: Page number (should be >= 1)
        per_page: Items per page (should be between 1 and max_per_page)
        max_per_page: Maximum allowed items per page

    Returns:
        Tuple of (validated_page, validated_per_page)

    Raises:
        ValidationError: If parameters are invalid
    """
    # Validate page
    if page is None:
        page = 1
    try:
        page = int(page)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'page' must be a valid integer, got: {page}",
            field="page"
        )

    if page < MIN_PAGE:
        raise ValidationError(
            f"'page' must be at least {MIN_PAGE}, got: {page}",
            field="page"
        )

    # Validate per_page
    if per_page is None:
        per_page = 100
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'per_page' must be a valid integer, got: {per_page}",
            field="per_page"
        )

    if per_page < MIN_PAGE_SIZE:
        raise ValidationError(
            f"'per_page' must be at least {MIN_PAGE_SIZE}, got: {per_page}",
            field="per_page"
        )

    if per_page > max_per_page:
        raise ValidationError(
            f"'per_page' cannot exceed {max_per_page}, got: {per_page}",
            field="per_page"
        )

    return page, per_page


def validate_driver_code(
    driver_code: Any,
    valid_drivers: dict,
    field_name: str = "driver_code"
) -> str:
    """
    Validate a driver code.

    Args:
        driver_code: The driver code to validate
        valid_drivers: Dictionary of valid driver codes
        field_name: Name of the field for error messages

    Returns:
        Validated driver code (uppercase)

    Raises:
        ValidationError: If driver code is invalid
    """
    if driver_code is None:
        raise ValidationError(
            f"'{field_name}' is required",
            field=field_name
        )

    if not isinstance(driver_code, str):
        raise ValidationError(
            f"'{field_name}' must be a string",
            field=field_name
        )

    driver_code = driver_code.strip().upper()

    if len(driver_code) != DRIVER_CODE_LENGTH:
        raise ValidationError(
            f"'{field_name}' must be a {DRIVER_CODE_LENGTH}-letter code, got: {driver_code}",
            field=field_name
        )

    if not driver_code.isalpha():
        raise ValidationError(
            f"'{field_name}' must contain only letters, got: {driver_code}",
            field=field_name
        )

    if driver_code not in valid_drivers:
        raise ValidationError(
            f"Unknown driver code: {driver_code}. Valid codes: {', '.join(sorted(valid_drivers.keys()))}",
            field=field_name
        )

    return driver_code


def validate_position(position: Any) -> int:
    """
    Validate a championship position.

    Args:
        position: The position to validate

    Returns:
        Validated position as integer

    Raises:
        ValidationError: If position is invalid
    """
    if position is None:
        raise ValidationError(
            "'position' parameter is required",
            field="position"
        )

    try:
        position = int(position)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'position' must be a valid integer, got: {position}",
            field="position"
        )

    if position < MIN_POSITION:
        raise ValidationError(
            f"'position' must be at least {MIN_POSITION}, got: {position}",
            field="position"
        )

    if position > MAX_POSITION:
        raise ValidationError(
            f"'position' cannot exceed {MAX_POSITION}, got: {position}",
            field="position"
        )

    return position


def validate_championship_id(championship_id: Any) -> int:
    """
    Validate a championship ID.

    Args:
        championship_id: The ID to validate

    Returns:
        Validated ID as integer

    Raises:
        ValidationError: If ID is invalid
    """
    if championship_id is None:
        raise ValidationError(
            "'id' parameter is required",
            field="id"
        )

    try:
        championship_id = int(championship_id)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'id' must be a valid integer, got: {championship_id}",
            field="id"
        )

    if championship_id < 1:
        raise ValidationError(
            f"'id' must be a positive integer, got: {championship_id}",
            field="id"
        )

    return championship_id


def validate_rounds(rounds_str: Any) -> List[int]:
    """
    Validate a comma-separated string of round numbers.

    Args:
        rounds_str: Comma-separated round numbers

    Returns:
        List of validated round numbers (sorted)

    Raises:
        ValidationError: If rounds are invalid
    """
    if rounds_str is None or rounds_str == '':
        raise ValidationError(
            "'rounds' parameter is required",
            field="rounds"
        )

    if not isinstance(rounds_str, str):
        raise ValidationError(
            "'rounds' must be a comma-separated string of numbers",
            field="rounds"
        )

    rounds_str = rounds_str.strip()

    if not rounds_str:
        raise ValidationError(
            "'rounds' cannot be empty",
            field="rounds"
        )

    try:
        round_numbers = [int(r.strip()) for r in rounds_str.split(',')]
    except ValueError:
        raise ValidationError(
            f"'rounds' must contain only valid integers separated by commas, got: {rounds_str}",
            field="rounds"
        )

    if not round_numbers:
        raise ValidationError(
            "'rounds' must contain at least one round number",
            field="rounds"
        )

    # Validate each round number
    invalid_rounds = [r for r in round_numbers if r < MIN_ROUND or r > MAX_ROUND]
    if invalid_rounds:
        raise ValidationError(
            f"Round numbers must be between {MIN_ROUND} and {MAX_ROUND}, invalid: {invalid_rounds}",
            field="rounds"
        )

    # Check for duplicates
    if len(round_numbers) != len(set(round_numbers)):
        raise ValidationError(
            "Duplicate round numbers are not allowed",
            field="rounds"
        )

    return sorted(round_numbers)


def validate_boolean(value: Any, field_name: str, default: bool = False) -> bool:
    """
    Validate a boolean parameter from query string.

    Args:
        value: The value to validate
        field_name: Name of the field for error messages
        default: Default value if None

    Returns:
        Validated boolean value
    """
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        lower_val = value.lower().strip()
        if lower_val in ('true', '1', 'yes', 'on'):
            return True
        if lower_val in ('false', '0', 'no', 'off', ''):
            return False

    raise ValidationError(
        f"'{field_name}' must be a boolean value (true/false), got: {value}",
        field=field_name
    )


def format_validation_error(error: ValidationError) -> dict:
    """
    Format a ValidationError into a JSON-serializable dict.

    Args:
        error: The ValidationError to format

    Returns:
        Dictionary with error details
    """
    result = {"error": error.message}
    if error.field:
        result["field"] = error.field
    return result
