"""
Input validation and error response utilities for API endpoints.

Provides consistent validation, error codes, and error messages across all endpoints.
"""
from typing import Tuple, Optional, List, Any, Dict
from enum import Enum


# =============================================================================
# Error Codes - Standardized codes for all API errors
# =============================================================================

class ErrorCode(str, Enum):
    """Standardized error codes for API responses."""

    # Validation errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PARAMETER = "INVALID_PARAMETER"
    MISSING_PARAMETER = "MISSING_PARAMETER"
    INVALID_FORMAT = "INVALID_FORMAT"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    DUPLICATE_VALUE = "DUPLICATE_VALUE"

    # Not found errors (404)
    NOT_FOUND = "NOT_FOUND"
    DRIVER_NOT_FOUND = "DRIVER_NOT_FOUND"
    CHAMPIONSHIP_NOT_FOUND = "CHAMPIONSHIP_NOT_FOUND"

    # Client errors (400)
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_DRIVER_COMPARISON = "INVALID_DRIVER_COMPARISON"

    # Server errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"


# =============================================================================
# Validation Constants
# =============================================================================

MAX_PAGE_SIZE = 1000
MIN_PAGE = 1
MIN_PAGE_SIZE = 1
MAX_POSITION = 24  # Maximum number of drivers
MIN_POSITION = 1
MAX_ROUND = 24  # Maximum number of races in a season
MIN_ROUND = 1
DRIVER_CODE_LENGTH = 3


# =============================================================================
# Exception Classes
# =============================================================================

class ValidationError(Exception):
    """Exception raised for validation errors."""

    def __init__(
        self,
        message: str,
        field: str = None,
        code: ErrorCode = ErrorCode.VALIDATION_ERROR
    ):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(self.message)


class NotFoundError(Exception):
    """Exception raised when a resource is not found."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.NOT_FOUND,
        resource_type: str = None,
        resource_id: Any = None
    ):
        self.message = message
        self.code = code
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(self.message)


# =============================================================================
# Standardized Error Response Builder
# =============================================================================

def build_error_response(
    code: ErrorCode,
    message: str,
    field: str = None,
    details: Dict = None,
    http_status: int = None
) -> Tuple[Dict, int]:
    """
    Build a standardized error response.

    Args:
        code: The error code from ErrorCode enum
        message: Human-readable error message
        field: Optional field name that caused the error
        details: Optional additional details
        http_status: Optional HTTP status code override

    Returns:
        Tuple of (error_dict, http_status_code)
    """
    error_body = {
        "code": code.value,
        "message": message
    }

    if field:
        error_body["field"] = field

    if details:
        error_body["details"] = details

    response = {"error": error_body}

    # Determine HTTP status from error code if not provided
    if http_status is None:
        if code in (ErrorCode.NOT_FOUND, ErrorCode.DRIVER_NOT_FOUND,
                    ErrorCode.CHAMPIONSHIP_NOT_FOUND):
            http_status = 404
        elif code in (ErrorCode.INTERNAL_ERROR, ErrorCode.DATABASE_ERROR):
            http_status = 500
        else:
            http_status = 400

    return response, http_status


def format_validation_error(error: ValidationError) -> Tuple[Dict, int]:
    """
    Format a ValidationError into a standardized error response.

    Args:
        error: The ValidationError to format

    Returns:
        Tuple of (error_dict, http_status_code)
    """
    return build_error_response(
        code=error.code,
        message=error.message,
        field=error.field
    )


def format_not_found_error(error: NotFoundError) -> Tuple[Dict, int]:
    """
    Format a NotFoundError into a standardized error response.

    Args:
        error: The NotFoundError to format

    Returns:
        Tuple of (error_dict, http_status_code)
    """
    details = None
    if error.resource_type or error.resource_id:
        details = {}
        if error.resource_type:
            details["resource_type"] = error.resource_type
        if error.resource_id is not None:
            details["resource_id"] = error.resource_id

    return build_error_response(
        code=error.code,
        message=error.message,
        details=details
    )


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
            field="page",
            code=ErrorCode.INVALID_FORMAT
        )

    if page < MIN_PAGE:
        raise ValidationError(
            f"'page' must be at least {MIN_PAGE}, got: {page}",
            field="page",
            code=ErrorCode.OUT_OF_RANGE
        )

    # Validate per_page
    if per_page is None:
        per_page = 100
    try:
        per_page = int(per_page)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'per_page' must be a valid integer, got: {per_page}",
            field="per_page",
            code=ErrorCode.INVALID_FORMAT
        )

    if per_page < MIN_PAGE_SIZE:
        raise ValidationError(
            f"'per_page' must be at least {MIN_PAGE_SIZE}, got: {per_page}",
            field="per_page",
            code=ErrorCode.OUT_OF_RANGE
        )

    if per_page > max_per_page:
        raise ValidationError(
            f"'per_page' cannot exceed {max_per_page}, got: {per_page}",
            field="per_page",
            code=ErrorCode.OUT_OF_RANGE
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
        NotFoundError: If driver code is not in valid_drivers
    """
    if driver_code is None:
        raise ValidationError(
            f"'{field_name}' is required",
            field=field_name,
            code=ErrorCode.MISSING_PARAMETER
        )

    if not isinstance(driver_code, str):
        raise ValidationError(
            f"'{field_name}' must be a string",
            field=field_name,
            code=ErrorCode.INVALID_FORMAT
        )

    driver_code = driver_code.strip().upper()

    if len(driver_code) != DRIVER_CODE_LENGTH:
        raise ValidationError(
            f"'{field_name}' must be a {DRIVER_CODE_LENGTH}-letter code, got: {driver_code}",
            field=field_name,
            code=ErrorCode.INVALID_FORMAT
        )

    if not driver_code.isalpha():
        raise ValidationError(
            f"'{field_name}' must contain only letters, got: {driver_code}",
            field=field_name,
            code=ErrorCode.INVALID_FORMAT
        )

    if driver_code not in valid_drivers:
        raise NotFoundError(
            f"Driver not found: {driver_code}",
            code=ErrorCode.DRIVER_NOT_FOUND,
            resource_type="driver",
            resource_id=driver_code
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
            field="position",
            code=ErrorCode.MISSING_PARAMETER
        )

    try:
        position = int(position)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'position' must be a valid integer, got: {position}",
            field="position",
            code=ErrorCode.INVALID_FORMAT
        )

    if position < MIN_POSITION:
        raise ValidationError(
            f"'position' must be at least {MIN_POSITION}, got: {position}",
            field="position",
            code=ErrorCode.OUT_OF_RANGE
        )

    if position > MAX_POSITION:
        raise ValidationError(
            f"'position' cannot exceed {MAX_POSITION}, got: {position}",
            field="position",
            code=ErrorCode.OUT_OF_RANGE
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
            field="id",
            code=ErrorCode.MISSING_PARAMETER
        )

    try:
        championship_id = int(championship_id)
    except (ValueError, TypeError):
        raise ValidationError(
            f"'id' must be a valid integer, got: {championship_id}",
            field="id",
            code=ErrorCode.INVALID_FORMAT
        )

    if championship_id < 1:
        raise ValidationError(
            f"'id' must be a positive integer, got: {championship_id}",
            field="id",
            code=ErrorCode.OUT_OF_RANGE
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
            field="rounds",
            code=ErrorCode.MISSING_PARAMETER
        )

    if not isinstance(rounds_str, str):
        raise ValidationError(
            "'rounds' must be a comma-separated string of numbers",
            field="rounds",
            code=ErrorCode.INVALID_FORMAT
        )

    rounds_str = rounds_str.strip()

    if not rounds_str:
        raise ValidationError(
            "'rounds' cannot be empty",
            field="rounds",
            code=ErrorCode.MISSING_PARAMETER
        )

    try:
        round_numbers = [int(r.strip()) for r in rounds_str.split(',')]
    except ValueError:
        raise ValidationError(
            f"'rounds' must contain only valid integers separated by commas, got: {rounds_str}",
            field="rounds",
            code=ErrorCode.INVALID_FORMAT
        )

    if not round_numbers:
        raise ValidationError(
            "'rounds' must contain at least one round number",
            field="rounds",
            code=ErrorCode.MISSING_PARAMETER
        )

    # Validate each round number
    invalid_rounds = [r for r in round_numbers if r < MIN_ROUND or r > MAX_ROUND]
    if invalid_rounds:
        raise ValidationError(
            f"Round numbers must be between {MIN_ROUND} and {MAX_ROUND}, invalid: {invalid_rounds}",
            field="rounds",
            code=ErrorCode.OUT_OF_RANGE
        )

    # Check for duplicates
    if len(round_numbers) != len(set(round_numbers)):
        raise ValidationError(
            "Duplicate round numbers are not allowed",
            field="rounds",
            code=ErrorCode.DUPLICATE_VALUE
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
        field=field_name,
        code=ErrorCode.INVALID_FORMAT
    )
