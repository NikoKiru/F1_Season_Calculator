"""Tests for validators module."""
import pytest
from championship.validators import (
    ErrorCode,
    ValidationError,
    NotFoundError,
    build_error_response,
    format_validation_error,
    format_not_found_error,
    validate_pagination,
    validate_driver_code,
    validate_position,
    validate_championship_id,
    validate_rounds,
    validate_boolean,
)


class TestErrorCode:
    """Test ErrorCode enum."""

    def test_error_codes_exist(self):
        """All expected error codes should exist."""
        assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
        assert ErrorCode.NOT_FOUND == "NOT_FOUND"
        assert ErrorCode.DRIVER_NOT_FOUND == "DRIVER_NOT_FOUND"
        assert ErrorCode.CHAMPIONSHIP_NOT_FOUND == "CHAMPIONSHIP_NOT_FOUND"
        assert ErrorCode.BAD_REQUEST == "BAD_REQUEST"
        assert ErrorCode.INTERNAL_ERROR == "INTERNAL_ERROR"


class TestValidationError:
    """Test ValidationError exception class."""

    def test_validation_error_with_message(self):
        """Should create error with message."""
        error = ValidationError("Test error")
        assert error.message == "Test error"
        assert error.field is None
        assert error.code == ErrorCode.VALIDATION_ERROR

    def test_validation_error_with_field(self):
        """Should create error with field."""
        error = ValidationError("Test error", field="page")
        assert error.field == "page"

    def test_validation_error_with_custom_code(self):
        """Should create error with custom code."""
        error = ValidationError("Test error", code=ErrorCode.OUT_OF_RANGE)
        assert error.code == ErrorCode.OUT_OF_RANGE


class TestNotFoundError:
    """Test NotFoundError exception class."""

    def test_not_found_error_basic(self):
        """Should create basic not found error."""
        error = NotFoundError("Resource not found")
        assert error.message == "Resource not found"
        assert error.code == ErrorCode.NOT_FOUND

    def test_not_found_error_with_resource(self):
        """Should create error with resource details."""
        error = NotFoundError(
            "Driver not found",
            code=ErrorCode.DRIVER_NOT_FOUND,
            resource_type="driver",
            resource_id="XXX"
        )
        assert error.resource_type == "driver"
        assert error.resource_id == "XXX"


class TestBuildErrorResponse:
    """Test build_error_response function."""

    def test_basic_response(self):
        """Should build basic error response."""
        response, status = build_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test error"
        )
        assert response["error"]["code"] == "VALIDATION_ERROR"
        assert response["error"]["message"] == "Test error"
        assert status == 400

    def test_response_with_field(self):
        """Should include field in response."""
        response, status = build_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test error",
            field="page"
        )
        assert response["error"]["field"] == "page"

    def test_response_with_details(self):
        """Should include details in response."""
        response, status = build_error_response(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test error",
            details={"key": "value"}
        )
        assert response["error"]["details"]["key"] == "value"

    def test_not_found_status(self):
        """Should return 404 for not found errors."""
        response, status = build_error_response(
            code=ErrorCode.NOT_FOUND,
            message="Not found"
        )
        assert status == 404

    def test_internal_error_status(self):
        """Should return 500 for internal errors."""
        response, status = build_error_response(
            code=ErrorCode.INTERNAL_ERROR,
            message="Internal error"
        )
        assert status == 500

    def test_custom_http_status(self):
        """Should respect custom HTTP status."""
        response, status = build_error_response(
            code=ErrorCode.BAD_REQUEST,
            message="Bad request",
            http_status=422
        )
        assert status == 422


class TestFormatValidationError:
    """Test format_validation_error function."""

    def test_format_validation_error(self):
        """Should format validation error correctly."""
        error = ValidationError("Invalid input", field="page")
        response, status = format_validation_error(error)
        assert response["error"]["message"] == "Invalid input"
        assert response["error"]["field"] == "page"
        assert status == 400


class TestFormatNotFoundError:
    """Test format_not_found_error function."""

    def test_format_not_found_error_basic(self):
        """Should format basic not found error."""
        error = NotFoundError("Resource not found")
        response, status = format_not_found_error(error)
        assert response["error"]["message"] == "Resource not found"
        assert status == 404

    def test_format_not_found_error_with_details(self):
        """Should include resource details."""
        error = NotFoundError(
            "Driver not found",
            resource_type="driver",
            resource_id="XXX"
        )
        response, status = format_not_found_error(error)
        assert response["error"]["details"]["resource_type"] == "driver"
        assert response["error"]["details"]["resource_id"] == "XXX"


class TestValidatePagination:
    """Test validate_pagination function."""

    def test_default_values(self):
        """Should use default values when None."""
        page, per_page = validate_pagination(None, None)
        assert page == 1
        assert per_page == 100

    def test_valid_values(self):
        """Should accept valid values."""
        page, per_page = validate_pagination(2, 50)
        assert page == 2
        assert per_page == 50

    def test_string_values(self):
        """Should convert string values."""
        page, per_page = validate_pagination("3", "25")
        assert page == 3
        assert per_page == 25

    def test_invalid_page_format(self):
        """Should raise error for invalid page format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pagination("abc", None)
        assert exc_info.value.field == "page"
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_page_below_minimum(self):
        """Should raise error for page below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pagination(0, None)
        assert exc_info.value.field == "page"
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE

    def test_invalid_per_page_format(self):
        """Should raise error for invalid per_page format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pagination(1, "abc")
        assert exc_info.value.field == "per_page"

    def test_per_page_below_minimum(self):
        """Should raise error for per_page below minimum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pagination(1, 0)
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE

    def test_per_page_above_maximum(self):
        """Should raise error for per_page above maximum."""
        with pytest.raises(ValidationError) as exc_info:
            validate_pagination(1, 10000)
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE


class TestValidateDriverCode:
    """Test validate_driver_code function."""

    def test_valid_driver(self):
        """Should accept valid driver code."""
        valid_drivers = {"VER": "Verstappen", "NOR": "Norris"}
        result = validate_driver_code("VER", valid_drivers)
        assert result == "VER"

    def test_lowercase_driver(self):
        """Should convert to uppercase."""
        valid_drivers = {"VER": "Verstappen"}
        result = validate_driver_code("ver", valid_drivers)
        assert result == "VER"

    def test_missing_driver(self):
        """Should raise error for None driver."""
        with pytest.raises(ValidationError) as exc_info:
            validate_driver_code(None, {"VER": "Verstappen"})
        assert exc_info.value.code == ErrorCode.MISSING_PARAMETER

    def test_non_string_driver(self):
        """Should raise error for non-string driver."""
        with pytest.raises(ValidationError) as exc_info:
            validate_driver_code(123, {"VER": "Verstappen"})
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_wrong_length_driver(self):
        """Should raise error for wrong length."""
        with pytest.raises(ValidationError) as exc_info:
            validate_driver_code("AB", {"VER": "Verstappen"})
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_non_alpha_driver(self):
        """Should raise error for non-alphabetic driver."""
        with pytest.raises(ValidationError) as exc_info:
            validate_driver_code("V3R", {"VER": "Verstappen"})
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_unknown_driver(self):
        """Should raise NotFoundError for unknown driver."""
        with pytest.raises(NotFoundError) as exc_info:
            validate_driver_code("XXX", {"VER": "Verstappen"})
        assert exc_info.value.code == ErrorCode.DRIVER_NOT_FOUND


class TestValidatePosition:
    """Test validate_position function."""

    def test_valid_position(self):
        """Should accept valid position."""
        result = validate_position(1)
        assert result == 1

    def test_string_position(self):
        """Should convert string to int."""
        result = validate_position("5")
        assert result == 5

    def test_missing_position(self):
        """Should raise error for None."""
        with pytest.raises(ValidationError) as exc_info:
            validate_position(None)
        assert exc_info.value.code == ErrorCode.MISSING_PARAMETER

    def test_invalid_format(self):
        """Should raise error for invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_position("abc")
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_below_minimum(self):
        """Should raise error for position below 1."""
        with pytest.raises(ValidationError) as exc_info:
            validate_position(0)
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE

    def test_above_maximum(self):
        """Should raise error for position above 24."""
        with pytest.raises(ValidationError) as exc_info:
            validate_position(25)
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE


class TestValidateChampionshipId:
    """Test validate_championship_id function."""

    def test_valid_id(self):
        """Should accept valid ID."""
        result = validate_championship_id(1)
        assert result == 1

    def test_string_id(self):
        """Should convert string to int."""
        result = validate_championship_id("42")
        assert result == 42

    def test_missing_id(self):
        """Should raise error for None."""
        with pytest.raises(ValidationError) as exc_info:
            validate_championship_id(None)
        assert exc_info.value.code == ErrorCode.MISSING_PARAMETER

    def test_invalid_format(self):
        """Should raise error for invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_championship_id("abc")
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_negative_id(self):
        """Should raise error for negative ID."""
        with pytest.raises(ValidationError) as exc_info:
            validate_championship_id(-1)
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE


class TestValidateRounds:
    """Test validate_rounds function."""

    def test_valid_rounds(self):
        """Should accept valid rounds."""
        result = validate_rounds("1,2,3")
        assert result == [1, 2, 3]

    def test_single_round(self):
        """Should accept single round."""
        result = validate_rounds("5")
        assert result == [5]

    def test_unsorted_rounds(self):
        """Should return sorted rounds."""
        result = validate_rounds("3,1,2")
        assert result == [1, 2, 3]

    def test_missing_rounds(self):
        """Should raise error for None."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds(None)
        assert exc_info.value.code == ErrorCode.MISSING_PARAMETER

    def test_empty_rounds(self):
        """Should raise error for empty string."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds("")
        assert exc_info.value.code == ErrorCode.MISSING_PARAMETER

    def test_invalid_format(self):
        """Should raise error for invalid format."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds("1,abc,3")
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT

    def test_out_of_range(self):
        """Should raise error for out of range rounds."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds("0,1,2")
        assert exc_info.value.code == ErrorCode.OUT_OF_RANGE

    def test_duplicate_rounds(self):
        """Should raise error for duplicate rounds."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds("1,2,2")
        assert exc_info.value.code == ErrorCode.DUPLICATE_VALUE

    def test_non_string_input(self):
        """Should raise error for non-string input."""
        with pytest.raises(ValidationError) as exc_info:
            validate_rounds(123)
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT


class TestValidateBoolean:
    """Test validate_boolean function."""

    def test_none_returns_default(self):
        """Should return default for None."""
        assert validate_boolean(None, "field") is False
        assert validate_boolean(None, "field", default=True) is True

    def test_boolean_values(self):
        """Should accept boolean values."""
        assert validate_boolean(True, "field") is True
        assert validate_boolean(False, "field") is False

    def test_string_true_values(self):
        """Should accept string true values."""
        for val in ("true", "TRUE", "1", "yes", "on"):
            assert validate_boolean(val, "field") is True

    def test_string_false_values(self):
        """Should accept string false values."""
        for val in ("false", "FALSE", "0", "no", "off", ""):
            assert validate_boolean(val, "field") is False

    def test_invalid_value(self):
        """Should raise error for invalid value."""
        with pytest.raises(ValidationError) as exc_info:
            validate_boolean("maybe", "field")
        assert exc_info.value.code == ErrorCode.INVALID_FORMAT
