"""
Unit tests for scalar converters in utilities.converters_scalar.

Tests cover conversion functions for basic Python types (int, float, bool, str)
and temporal types (date, datetime, Decimal).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest

from quicken_helper.utilities.converters_scalar import (
    _to_bool,  # type: ignore[reportPrivateUsage]
    _to_float,  # type: ignore[reportPrivateUsage]
    _to_int,  # type: ignore[reportPrivateUsage]
    _to_str,  # type: ignore[reportPrivateUsage]
    clean_number_like_string,
    default_date,
    to_date,
    to_datetime,
    to_decimal,
)

# ============================================================================
# to_decimal tests
# ============================================================================


def test_to_decimal_from_decimal_returns_same() -> None:
    """
    Positive: Decimal input returns unchanged.
    """
    # Arrange
    d = Decimal("123.45")
    # Act
    result = to_decimal(d)
    # Assert
    assert result == d
    assert result is d


def test_to_decimal_from_int() -> None:
    """
    Positive: Integer converts to exact Decimal.
    """
    # Arrange
    value = 42
    # Act
    result = to_decimal(value)
    # Assert
    assert result == Decimal("42")


def test_to_decimal_from_float() -> None:
    """
    Positive: Float converts via string to avoid binary artifacts.
    """
    # Arrange
    value = 3.14
    # Act
    result = to_decimal(value)
    # Assert
    assert result == Decimal("3.14")


def test_to_decimal_us_format_with_comma_thousands() -> None:
    """
    Positive: US-style "1,234.56" parsed correctly.
    """
    # Act
    result = to_decimal("1,234.56")
    # Assert
    assert result == Decimal("1234.56")


def test_to_decimal_eu_format_with_dot_thousands() -> None:
    """
    Positive: EU-style "1.234,56" - documents actual behavior.

    NOTE: to_decimal() internally calls clean_number_like_string with decimal_char="."
    (hardcoded), NOT auto-detection. This means:
    - Dot is always treated as decimal separator
    - Comma is always treated as thousands separator (removed)
    - "1.234,56" -> "1.23456" (not the EU interpretation of 1234.56)

    For true auto-detection, use clean_number_like_string(value, "") directly.
    This test documents the current to_decimal behavior.
    """
    # Act
    result = to_decimal("1.234,56")
    # Assert - documents current behavior where dot=decimal, comma removed
    assert result == Decimal("1.23456")


def test_to_decimal_parentheses_indicate_negative() -> None:
    """
    Positive: Parentheses like "(123.45)" indicate negative.
    """
    # Act
    result = to_decimal("(123.45)")
    # Assert
    assert result == Decimal("-123.45")


def test_to_decimal_trailing_minus_indicates_negative() -> None:
    """
    Positive: Trailing minus "123.45-" indicates negative.
    """
    # Act
    result = to_decimal("123.45-")
    # Assert
    assert result == Decimal("-123.45")


def test_to_decimal_with_currency_symbol() -> None:
    """
    Positive: Currency symbols like "$1,234.56" are stripped.
    """
    # Act
    result = to_decimal("$1,234.56")
    # Assert
    assert result == Decimal("1234.56")


def test_to_decimal_with_spaces_and_nbsp() -> None:
    """
    Positive: Whitespace and non-breaking spaces are stripped.
    """
    # Act
    result = to_decimal("  1\xa0234.56  ")  # \xa0 = NBSP
    # Assert
    assert result == Decimal("1234.56")


def test_to_decimal_empty_string_raises() -> None:
    """
    Negative: Empty string raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Empty string"):
        to_decimal("")


def test_to_decimal_no_digits_raises() -> None:
    """
    Negative: String with no digits raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="No digits found"):
        to_decimal("abc")


def test_to_decimal_unsupported_type_raises() -> None:
    """
    Negative: Non-numeric, non-string type raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Unsupported type"):
        to_decimal([1, 2, 3])


# ============================================================================
# clean_number_like_string tests
# ============================================================================


def test_clean_number_like_string_us_format() -> None:
    """
    Positive: US format "1,234.56" cleans to "1234.56".
    """
    # Act
    result = clean_number_like_string("1,234.56", ".")
    # Assert
    assert result == "1234.56"


def test_clean_number_like_string_eu_format() -> None:
    """
    Positive: EU format "1.234,56" cleans to "1234.56" when decimal_char=",".
    """
    # Act
    result = clean_number_like_string("1.234,56", ",")
    # Assert
    assert result == "1234.56"


def test_clean_number_like_string_auto_detect_decimal() -> None:
    """
    Positive: Auto-detects decimal separator (last separator used).
    """
    # Act - both comma and dot present, dot is last
    result1 = clean_number_like_string("1,234.56", "")
    # Act - comma is last
    result2 = clean_number_like_string("1.234,56", "")
    # Assert
    assert result1 == "1234.56"
    assert result2 == "1234.56"


def test_clean_number_like_string_negative_with_parentheses() -> None:
    """
    Positive: Parentheses "(123)" convert to "-123".
    """
    # Act
    result = clean_number_like_string("(123)", ".")
    # Assert
    assert result == "-123"


def test_clean_number_like_string_trailing_minus() -> None:
    """
    Positive: Trailing minus "123-" converts to "-123".
    """
    # Act
    result = clean_number_like_string("123-", ".")
    # Assert
    assert result == "-123"


def test_clean_number_like_string_unicode_minus() -> None:
    """
    Positive: Unicode minus sign (U+2212) normalized to ASCII '-'.
    """
    # Act
    result = clean_number_like_string("\u2212123", ".")
    # Assert
    assert result == "-123"


def test_clean_number_like_string_invalid_decimal_char_raises() -> None:
    """
    Negative: Invalid decimal_char raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Invalid decimal_char"):
        clean_number_like_string("123", "x")


def test_clean_number_like_string_empty_raises() -> None:
    """
    Negative: Empty string raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Empty string"):
        clean_number_like_string("", ".")


# ============================================================================
# _to_int tests
# ============================================================================


def test_to_int_from_int_returns_same() -> None:
    """
    Positive: int input returns unchanged.
    """
    # Arrange
    value = 42
    # Act
    result = _to_int(value)
    # Assert
    assert result == 42
    assert isinstance(result, int)


def test_to_int_from_bool_when_allowed() -> None:
    """
    Positive: bool converts to int (0 or 1) when _ALLOW_BOOL_TO_INT is True.
    """
    # Act
    result_true = _to_int(True)
    result_false = _to_int(False)
    # Assert
    assert result_true == 1
    assert result_false == 0


def test_to_int_from_decimal() -> None:
    """
    Positive: Decimal converts to int (truncating fractional part).
    """
    # Arrange
    value = Decimal("42.99")
    # Act
    result = _to_int(value)
    # Assert
    assert result == 42


def test_to_int_from_float_integer_value() -> None:
    """
    Positive: Float with integer value (e.g., 5.0) converts to int.
    """
    # Act
    result = _to_int(5.0)
    # Assert
    assert result == 5


def test_to_int_from_float_non_integer_raises() -> None:
    """
    Negative: Float with fractional part raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Non-integer float"):
        _to_int(3.14)


def test_to_int_from_string() -> None:
    """
    Positive: Numeric string converts to int.
    """
    # Act
    result = _to_int("42")
    # Assert
    assert result == 42


def test_to_int_from_string_with_commas() -> None:
    """
    Positive: String with commas like "1,234" converts to int.
    """
    # Act
    result = _to_int("1,234")
    # Assert
    assert result == 1234


def test_to_int_unsupported_type_raises() -> None:
    """
    Negative: Unsupported type raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Unsupported type"):
        _to_int([1, 2, 3])


# ============================================================================
# _to_float tests
# ============================================================================


def test_to_float_from_float_returns_same() -> None:
    """
    Positive: float input returns unchanged.
    """
    # Arrange
    value = 3.14
    # Act
    result = _to_float(value)
    # Assert
    assert result == 3.14


def test_to_float_from_int() -> None:
    """
    Positive: int converts to float.
    """
    # Act
    result = _to_float(42)
    # Assert
    assert result == 42.0


def test_to_float_from_bool() -> None:
    """
    Positive: bool converts to float (0.0 or 1.0).
    """
    # Act
    result_true = _to_float(True)
    result_false = _to_float(False)
    # Assert
    assert result_true == 1.0
    assert result_false == 0.0


def test_to_float_from_decimal() -> None:
    """
    Positive: Decimal converts to float.
    """
    # Act
    result = _to_float(Decimal("123.45"))
    # Assert
    assert result == 123.45


def test_to_float_from_string() -> None:
    """
    Positive: Numeric string converts to float.
    """
    # Act
    result = _to_float("3.14")
    # Assert
    assert result == 3.14


def test_to_float_unsupported_type_raises() -> None:
    """
    Negative: Unsupported type raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError):
        _to_float([1.0, 2.0])


# ============================================================================
# _to_bool tests
# ============================================================================


def test_to_bool_from_bool_returns_same() -> None:
    """
    Positive: bool input returns unchanged.
    """
    # Act
    result_true = _to_bool(True)
    result_false = _to_bool(False)
    # Assert
    assert result_true is True
    assert result_false is False


@pytest.mark.parametrize(
    "value",
    ["1", "true", "True", "TRUE", "t", "T", "yes", "Yes", "YES", "y", "Y", "on", "ON"],
)
def test_to_bool_truthy_strings(value: str):
    """
    Positive: Various truthy string representations convert to True.
    """
    # Act
    result = _to_bool(value)
    # Assert
    assert result is True


@pytest.mark.parametrize(
    "value",
    [
        "0",
        "false",
        "False",
        "FALSE",
        "f",
        "F",
        "no",
        "No",
        "NO",
        "n",
        "N",
        "off",
        "anything",
    ],
)
def test_to_bool_falsy_strings(value: str):
    """
    Positive: Non-truthy strings convert to False.
    """
    # Act
    result = _to_bool(value)
    # Assert
    assert result is False


def test_to_bool_from_numeric_nonzero() -> None:
    """
    Positive: Non-zero numeric values convert to True.
    """
    # Act
    result1 = _to_bool(1)
    result2 = _to_bool(42)
    result3 = _to_bool(3.14)
    result4 = _to_bool(Decimal("1.0"))
    # Assert
    assert result1 is True
    assert result2 is True
    assert result3 is True
    assert result4 is True


def test_to_bool_from_numeric_zero() -> None:
    """
    Positive: Zero numeric values convert to False.
    """
    # Act
    result1 = _to_bool(0)
    result2 = _to_bool(0.0)
    result3 = _to_bool(Decimal("0"))
    # Assert
    assert result1 is False
    assert result2 is False
    assert result3 is False


def test_to_bool_unsupported_type_raises() -> None:
    """
    Negative: Unsupported type raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError):
        _to_bool([True, False])


# ============================================================================
# _to_str tests
# ============================================================================


def test_to_str_from_string_returns_same() -> None:
    """
    Positive: String input returns unchanged.
    """
    # Act
    result = _to_str("hello")
    # Assert
    assert result == "hello"


def test_to_str_from_none() -> None:
    """
    Edge: None converts to empty string.
    """
    # Act
    result = _to_str(None)
    # Assert
    assert result == ""


def test_to_str_from_int() -> None:
    """
    Positive: int converts to string representation.
    """
    # Act
    result = _to_str(42)
    # Assert
    assert result == "42"


def test_to_str_from_float() -> None:
    """
    Positive: float converts to string representation.
    """
    # Act
    result = _to_str(3.14)
    # Assert
    assert result == "3.14"


def test_to_str_from_decimal() -> None:
    """
    Positive: Decimal converts to string representation.
    """
    # Act
    result = _to_str(Decimal("123.45"))
    # Assert
    assert result == "123.45"


# ============================================================================
# to_date tests
# ============================================================================


def test_to_date_from_date_returns_same() -> None:
    """
    Positive: date input returns unchanged.
    """
    # Arrange
    d = date(2025, 1, 15)
    # Act
    result = to_date(d)
    # Assert
    assert result == d


def test_to_date_from_datetime() -> None:
    """
    Positive: datetime converts to date (ignoring time).
    """
    # Arrange
    dt = datetime(2025, 1, 15, 14, 30, 0)
    # Act
    result = to_date(dt)
    # Assert
    assert result == date(2025, 1, 15)


def test_to_date_from_iso_string() -> None:
    """
    Positive: ISO format "2025-01-15" parses correctly.
    """
    # Act
    result = to_date("2025-01-15")
    # Assert
    assert result == date(2025, 1, 15)


def test_to_date_from_us_format() -> None:
    """
    Positive: US format "12/31/2024" parses correctly.
    """
    # Act
    result = to_date("12/31/2024")
    # Assert
    assert result == date(2024, 12, 31)


def test_to_date_from_qif_apostrophe_format() -> None:
    """
    Positive: QIF format "12/31'24" parses correctly.
    """
    # Act
    result = to_date("12/31'24")
    # Assert
    assert result == date(2024, 12, 31)


def test_to_date_from_iso_compact() -> None:
    """
    Positive: ISO compact format "20250115" parses correctly.
    """
    # Act
    result = to_date("20250115")
    # Assert
    assert result == date(2025, 1, 15)


def test_to_date_from_excel_serial() -> None:
    """
    Positive: Excel serial date (e.g., 45567) converts correctly.
    """
    # Excel serial 45567 corresponds to 2024-10-02 in the 1900 date system
    # Act
    result = to_date("45567")
    # Assert
    assert result == date(2024, 10, 2)


def test_to_date_from_iso_datetime_with_time() -> None:
    """
    Positive: ISO datetime with time and Z suffix parses (time ignored).
    """
    # Act
    result = to_date("2025-01-15T14:30:00Z")
    # Assert
    assert result == date(2025, 1, 15)


def test_to_date_none_returns_default() -> None:
    """
    Edge: None returns default date (1900-01-01).
    """
    # Act
    result = to_date(None, False)  # type: ignore[arg-type]
    # Assert
    assert result == date(1900, 1, 1)


def test_to_date_empty_string_returns_default() -> None:
    """
    Edge: Empty string returns default date (1900-01-01).
    """
    # Act
    result = to_date("", False)
    # Assert
    assert result == date(1900, 1, 1)


def test_to_date_unrecognized_raises() -> None:
    """
    Negative: Unrecognized format raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError, match="Unrecognized date format"):
        to_date("not-a-date", True)


def test_to_date_unrecognized_returns_default_when_not_raising() -> None:
    """
    Edge: Unrecognized format returns default when should_raise=False.
    """
    # Act
    result = to_date("not-a-date", False)
    # Assert
    assert result == date(1900, 1, 1)


def test_default_date_returns_1900_01_01() -> None:
    """
    Positive: default_date() returns the sentinel date.
    """
    # Act
    result = default_date()
    # Assert
    assert result == date(1900, 1, 1)


# ============================================================================
# to_datetime tests
# ============================================================================


def test_to_datetime_from_datetime_returns_same() -> None:
    """
    Positive: datetime input returns unchanged.
    """
    # Arrange
    dt = datetime(2025, 1, 15, 14, 30, 0)
    # Act
    result = to_datetime(dt)
    # Assert
    assert result == dt


def test_to_datetime_from_date() -> None:
    """
    Positive: date converts to datetime at midnight.
    """
    # Arrange
    d = date(2025, 1, 15)
    # Act
    result = to_datetime(d)
    # Assert
    assert result == datetime(2025, 1, 15, 0, 0, 0)


def test_to_datetime_from_posix_timestamp_int() -> None:
    """
    Positive: POSIX timestamp (int) converts to local datetime.
    """
    # Arrange - use a known timestamp
    timestamp = 1609459200  # 2021-01-01 00:00:00 UTC (approximately)
    # Act
    result = to_datetime(timestamp)
    # Assert
    # Exact result depends on local timezone, so check structure
    assert isinstance(result, datetime)
    # Should be close to 2021-01-01
    assert result.year in (2020, 2021)


def test_to_datetime_from_posix_timestamp_float() -> None:
    """
    Positive: POSIX timestamp (float) converts to local datetime.
    """
    # Arrange
    timestamp = 1609459200.5
    # Act
    result = to_datetime(timestamp)
    # Assert
    assert isinstance(result, datetime)
    assert result.microsecond > 0  # fractional seconds preserved


def test_to_datetime_from_iso_string() -> None:
    """
    Positive: ISO format string parses correctly.
    """
    # Act
    result = to_datetime("2025-01-15T14:30:00")
    # Assert
    assert result == datetime(2025, 1, 15, 14, 30, 0)


def test_to_datetime_from_iso_string_with_z() -> None:
    """
    Positive: ISO format with trailing 'Z' parses correctly (Z converted to +00:00).
    """
    # Act
    result = to_datetime("2025-01-15T14:30:00Z")
    # Assert
    # Z is converted to +00:00, which creates an aware datetime
    assert result.year == 2025
    assert result.month == 1
    assert result.day == 15
    assert result.hour == 14
    assert result.minute == 30


def test_to_datetime_invalid_string_raises() -> None:
    """
    Negative: Invalid string raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError):
        to_datetime("not-a-datetime")


def test_to_datetime_unsupported_type_raises() -> None:
    """
    Negative: Unsupported type raises ValueError.
    """
    # Assert
    with pytest.raises(ValueError):
        to_datetime([2025, 1, 15])  # type: ignore[arg-type]
