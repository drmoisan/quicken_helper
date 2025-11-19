"""
Unit tests for collection converters in utilities.converters_collection.

Tests cover conversion functions for parameterized collections:
list, set, frozenset, tuple, dict, and deque.
"""

from __future__ import annotations

from collections import deque

import pytest

from quicken_helper.utilities.converters_collection import (
    _to_deque,
    _to_dict,
    _to_frozenset,
    _to_list,
    _to_set,
    _to_tuple,
)


def _identity_converter(target_type: object, value: object) -> object:
    """
    Mock converter that returns value unchanged.
    Used for testing collection structure without type conversion.
    """
    return value


def _int_converter(target_type: object, value: object) -> int:
    """
    Mock converter that converts value to int.
    """
    return int(value)  # type: ignore[arg-type]


def _str_converter(target_type: object, value: object) -> str:
    """
    Mock converter that converts value to str.
    """
    return str(value)


# ============================================================================
# _to_list tests
# ============================================================================


def test_to_list_empty_iterable():
    """
    Positive: Empty iterable converts to empty list.
    """
    # Arrange
    args = (int,)
    value: list[object] = []
    # Act
    result = _to_list(args, value, _int_converter)
    # Assert
    assert result == []


def test_to_list_converts_elements():
    """
    Positive: Elements are converted using provided converter.
    """
    # Arrange
    args = (int,)
    value = ["1", "2", "3"]
    # Act
    result = _to_list(args, value, _int_converter)
    # Assert
    assert result == [1, 2, 3]
    assert all(isinstance(x, int) for x in result)


def test_to_list_no_type_args_defaults_to_object():
    """
    Edge: Empty args tuple defaults to object type.
    """
    # Arrange
    args: tuple[type, ...] = ()
    value = [1, "two", 3.0]
    # Act
    result = _to_list(args, value, _identity_converter)
    # Assert
    assert result == [1, "two", 3.0]


def test_to_list_treats_string_as_atomic():
    """
    Edge: String input treated as single element, not iterated.
    """
    # Arrange
    args = (str,)
    value = "hello"
    # Act
    result = _to_list(args, value, _identity_converter)
    # Assert
    assert result == ["hello"]


def test_to_list_treats_bytes_as_atomic():
    """
    Edge: Bytes input treated as single element, not iterated.
    """
    # Arrange
    args = (bytes,)
    value = b"hello"
    # Act
    result = _to_list(args, value, _identity_converter)
    # Assert
    assert result == [b"hello"]


def test_to_list_non_iterable_raises():
    """
    Negative: Non-iterable input raises TypeError.
    """
    # Arrange
    args = (int,)
    value = 123
    # Assert
    with pytest.raises(TypeError, match="Expected an iterable"):
        _to_list(args, value, _int_converter)


# ============================================================================
# _to_set tests
# ============================================================================


def test_to_set_empty_iterable():
    """
    Positive: Empty iterable converts to empty set.
    """
    # Arrange
    args = (int,)
    value: list[object] = []
    # Act
    result = _to_set(args, value, _int_converter)
    # Assert
    assert result == set()


def test_to_set_converts_elements():
    """
    Positive: Elements are converted using provided converter.
    """
    # Arrange
    args = (int,)
    value = ["1", "2", "3", "2"]
    # Act
    result = _to_set(args, value, _int_converter)
    # Assert
    assert result == {1, 2, 3}


def test_to_set_treats_string_as_atomic():
    """
    Edge: String input treated as single element.
    """
    # Arrange
    args = (str,)
    value = "hello"
    # Act
    result = _to_set(args, value, _identity_converter)
    # Assert
    assert result == {"hello"}


def test_to_set_non_iterable_raises():
    """
    Negative: Non-iterable input raises TypeError.
    """
    # Arrange
    args = (int,)
    value = 123
    # Assert
    with pytest.raises(TypeError, match="Expected an iterable"):
        _to_set(args, value, _int_converter)


def test_to_set_unhashable_elements_raises():
    """
    Negative: Unhashable elements after conversion raise TypeError.
    """
    # Arrange
    args = (list,)
    value = [[1], [2]]

    def _list_converter(target_type: object, value: object) -> list[object]:
        return list(value)  # type: ignore[arg-type]

    # Assert
    with pytest.raises(TypeError, match="Unhashable element"):
        _to_set(args, value, _list_converter)


# ============================================================================
# _to_frozenset tests
# ============================================================================


def test_to_frozenset_empty_iterable():
    """
    Positive: Empty iterable converts to empty frozenset.
    """
    # Arrange
    args = (int,)
    value: list[object] = []
    # Act
    result = _to_frozenset(args, value, _int_converter)
    # Assert
    assert result == frozenset()


def test_to_frozenset_converts_elements():
    """
    Positive: Elements are converted using provided converter.
    """
    # Arrange
    args = (int,)
    value = ["1", "2", "3", "2"]
    # Act
    result = _to_frozenset(args, value, _int_converter)
    # Assert
    assert result == frozenset({1, 2, 3})


def test_to_frozenset_treats_string_as_atomic():
    """
    Edge: String input treated as single element.
    """
    # Arrange
    args = (str,)
    value = "hello"
    # Act
    result = _to_frozenset(args, value, _identity_converter)
    # Assert
    assert result == frozenset({"hello"})


def test_to_frozenset_non_iterable_raises():
    """
    Negative: Non-iterable input raises TypeError.
    """
    # Arrange
    args = (int,)
    value = 123
    # Assert
    with pytest.raises(TypeError, match="Expected an iterable"):
        _to_frozenset(args, value, _int_converter)


def test_to_frozenset_unhashable_elements_raises():
    """
    Negative: Unhashable elements after conversion raise TypeError.
    """
    # Arrange
    args = (list,)
    value = [[1], [2]]

    def _list_converter(target_type: object, value: object) -> list[object]:
        return list(value)  # type: ignore[arg-type]

    # Assert
    with pytest.raises(TypeError, match="Unhashable element"):
        _to_frozenset(args, value, _list_converter)


# ============================================================================
# _to_tuple tests
# ============================================================================


def test_to_tuple_empty_iterable():
    """
    Positive: Empty iterable converts to empty tuple.
    """
    # Arrange
    args = (int,)
    value: list[object] = []
    # Act
    result = _to_tuple(args, value, _int_converter)
    # Assert
    assert result == ()


def test_to_tuple_converts_elements():
    """
    Positive: Elements are converted using provided converter (variadic tuple).
    """
    # Arrange
    args = (int, ...)  # Variadic: apply int to all elements
    value = ["1", "2", "3"]
    # Act
    result = _to_tuple(args, value, _int_converter)
    # Assert
    assert result == (1, 2, 3)
    assert all(isinstance(x, int) for x in result)


def test_to_tuple_treats_string_as_atomic():
    """
    Edge: String input treated as single element.
    """
    # Arrange
    args = (str,)
    value = "hello"
    # Act
    result = _to_tuple(args, value, _identity_converter)
    # Assert
    assert result == ("hello",)


def test_to_tuple_non_iterable_raises():
    """
    Negative: Non-iterable input raises TypeError.
    """
    # Arrange
    args = (int,)
    value = 123
    # Assert
    with pytest.raises(TypeError, match="Expected an iterable"):
        _to_tuple(args, value, _int_converter)


# ============================================================================
# _to_dict tests
# ============================================================================


def test_to_dict_empty_mapping():
    """
    Positive: Empty mapping converts to empty dict.
    """
    # Arrange
    args = (str, int)
    value: dict[str, str] = {}
    # Act
    result = _to_dict(args, value, _identity_converter)
    # Assert
    assert result == {}


def test_to_dict_from_mapping():
    """
    Positive: Mapping converts with key and value conversion.
    """
    # Arrange
    args = (str, int)
    value = {"a": "1", "b": "2"}

    def _mixed_converter(target_type: object, value: object) -> object:
        """Converter that handles both str and int conversions."""
        if target_type is str:
            return str(value)
        elif target_type is int:
            return int(value)  # type: ignore[arg-type]
        return value

    # Act
    result = _to_dict(args, value, _mixed_converter)
    # Assert
    assert result == {"a": 1, "b": 2}


def test_to_dict_from_iterable_of_pairs():
    """
    Positive: Iterable of 2-item pairs converts to dict.
    """
    # Arrange
    args = (str, int)
    value = [("a", "1"), ("b", "2")]

    def _mixed_converter(target_type: object, value: object) -> object:
        """Converter that handles both str and int conversions."""
        if target_type is str:
            return str(value)
        elif target_type is int:
            return int(value)  # type: ignore[arg-type]
        return value

    # Act
    result = _to_dict(args, value, _mixed_converter)
    # Assert
    assert result == {"a": 1, "b": 2}


def test_to_dict_no_args_defaults_to_object():
    """
    Edge: Empty args defaults to (object, object).
    """
    # Arrange
    args: tuple[type, ...] = ()
    value = {"a": 1, "b": 2}
    # Act
    result = _to_dict(args, value, _identity_converter)
    # Assert
    assert result == {"a": 1, "b": 2}


def test_to_dict_one_arg_uses_object_for_value():
    """
    Edge: Single arg in args defaults value type to object.
    """
    # Arrange
    args = (str,)
    value = {"a": 1, "b": 2}
    # Act
    result = _to_dict(args, value, _identity_converter)
    # Assert
    assert result == {"a": 1, "b": 2}


def test_to_dict_string_input_raises():
    """
    Negative: String input (atomic) raises TypeError.
    """
    # Arrange
    args = (str, int)
    value = "not-a-mapping"
    # Assert
    with pytest.raises(TypeError, match="Expected a mapping"):
        _to_dict(args, value, _int_converter)


def test_to_dict_bytes_input_raises():
    """
    Negative: Bytes input (atomic) raises TypeError.
    """
    # Arrange
    args = (str, int)
    value = b"not-a-mapping"
    # Assert
    with pytest.raises(TypeError, match="Expected a mapping"):
        _to_dict(args, value, _int_converter)


def test_to_dict_iterable_non_pair_elements_raises():
    """
    Negative: Iterable with non-2-item elements raises TypeError.
    """
    # Arrange
    args = (str, int)
    value = [("a", "1", "extra")]
    # Assert
    with pytest.raises(TypeError, match="not a 2-item pair"):
        _to_dict(args, value, _int_converter)


def test_to_dict_unhashable_keys_raises():
    """
    Negative: Unhashable keys after conversion raise TypeError.
    """
    # Arrange
    args = (list, int)
    value = {("a",): 1}

    def _list_key_converter(target_type: object, value: object) -> object:
        """Converter that converts tuple keys to lists (unhashable)."""
        if target_type is list and isinstance(value, tuple):
            return list(value)  # Convert tuple to list (unhashable)
        elif target_type is int:
            return int(value)  # type: ignore[arg-type]
        return value

    # Assert
    with pytest.raises(TypeError, match="Unhashable key"):
        _to_dict(args, value, _list_key_converter)


# ============================================================================
# _to_deque tests
# ============================================================================


def test_to_deque_empty_iterable():
    """
    Positive: Empty iterable converts to empty deque.
    """
    # Arrange
    args = (int,)
    value: list[object] = []
    # Act
    result = _to_deque(args, value, _int_converter)
    # Assert
    assert result == deque()


def test_to_deque_converts_elements():
    """
    Positive: Elements are converted using provided converter.
    """
    # Arrange
    args = (int,)
    value = ["1", "2", "3"]
    # Act
    result = _to_deque(args, value, _int_converter)
    # Assert
    assert result == deque([1, 2, 3])
    assert all(isinstance(x, int) for x in result)


def test_to_deque_treats_string_as_atomic():
    """
    Edge: String input treated as single element.
    """
    # Arrange
    args = (str,)
    value = "hello"
    # Act
    result = _to_deque(args, value, _identity_converter)
    # Assert
    assert result == deque(["hello"])


def test_to_deque_non_iterable_raises():
    """
    Negative: Non-iterable input raises TypeError.
    """
    # Arrange
    args = (int,)
    value = 123
    # Assert
    with pytest.raises(TypeError, match="Expected an iterable"):
        _to_deque(args, value, _int_converter)
