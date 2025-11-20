# tests/data_model/test_qif_sections.py
from quicken_helper.data_model import QuickenSections as QS

# ---------------------------
# has_flag
# ---------------------------


def test_has_flag_true_when_bit_set() -> None:
    """Test has_flag returns True when the specified bit is set in the mask."""
    # Arrange
    mask = QS.ACCOUNTS | QS.CATEGORIES

    # Act
    result = mask.has_flag(QS.ACCOUNTS)

    # Assert
    assert result is True, "has_flag should be True when the bit is present."


def test_has_flag_false_when_bit_not_set() -> None:
    """Test has_flag returns False when the specified bit is not set in the mask."""
    # Arrange
    mask = QS.ACCOUNTS  # CATEGORIES not included

    # Act
    result = mask.has_flag(QS.CATEGORIES)

    # Assert
    assert result is False, "has_flag should be False when the bit is missing."


# ---------------------------
# has_flags
# ---------------------------


def test_has_flags_true_when_all_bits_present() -> None:
    """Test has_flags returns True only when all required bits are present."""
    # Arrange
    mask = QS.ACCOUNTS | QS.CATEGORIES | QS.TAGS
    required = [QS.ACCOUNTS, QS.CATEGORIES]

    # Act
    result = mask.has_flags(required)

    # Assert
    assert result is True, "has_flags should be True only when ALL bits are present."


def test_has_flags_false_when_any_bit_missing() -> None:
    """Test has_flags returns False if any required bit is missing from the mask."""
    # Arrange
    mask = QS.ACCOUNTS | QS.TAGS
    required = [QS.ACCOUNTS, QS.CATEGORIES]  # CATEGORIES missing

    # Act
    result = mask.has_flags(required)

    # Assert
    assert result is False, "has_flags should be False if any required bit is missing."


def test_has_flags_empty_iterable_returns_true() -> None:
    """Test has_flags returns True for empty requirements by convention."""
    # Arrange
    mask = QS.ACCOUNTS  # value doesn't matter here

    # Act
    result = mask.has_flags([])

    # Assert
    assert result is True, "By convention, requiring no flags should return True."


# ---------------------------
# add_flag
# ---------------------------


def test_add_flag_returns_new_mask_with_bit_set() -> None:
    """Test add_flag returns immutable new mask with specified bit set."""
    # Arrange
    original = QS.NONE
    expected = QS.ACCOUNTS

    # Act
    new_mask = original.add_flag(QS.ACCOUNTS)

    # Assert
    assert (
        new_mask == expected
    ), "add_flag should set the requested bit on the returned mask."
    assert original == QS.NONE, "add_flag must be immutable (original mask unchanged)."


def test_add_flag_idempotent_when_bit_already_present() -> None:
    """Test add_flag is idempotent when the bit is already set."""
    # Arrange
    original = QS.ACCOUNTS
    expected = QS.ACCOUNTS

    # Act
    new_mask = original.add_flag(QS.ACCOUNTS)

    # Assert
    assert (
        new_mask == expected
    ), "add_flag should be idempotent when the bit is already present."


# ---------------------------
# add_flags
# ---------------------------


def test_add_flags_returns_new_mask_with_all_bits_set() -> None:
    """Test add_flags returns immutable new mask with all specified bits set."""
    # Arrange
    original = QS.NONE
    to_add = [QS.ACCOUNTS, QS.CATEGORIES, QS.TAGS]
    expected = QS.ACCOUNTS | QS.CATEGORIES | QS.TAGS

    # Act
    new_mask = original.add_flags(to_add)

    # Assert
    assert (
        new_mask == expected
    ), "add_flags should set ALL provided bits on the returned mask."
    assert original == QS.NONE, "add_flags must be immutable (original mask unchanged)."


# ---------------------------
# remove_flag
# ---------------------------


def test_remove_flag_returns_new_mask_with_bit_cleared() -> None:
    """Test remove_flag returns immutable new mask with specified bit cleared."""
    # Arrange
    original = QS.ACCOUNTS | QS.CATEGORIES
    expected = QS.CATEGORIES  # ACCOUNTS cleared

    # Act
    new_mask = original.remove_flag(QS.ACCOUNTS)

    # Assert
    assert (
        new_mask == expected
    ), "remove_flag should clear only the requested bit on the returned mask."
    assert original == (
        QS.ACCOUNTS | QS.CATEGORIES
    ), "remove_flag must be immutable (original mask unchanged)."


def test_remove_flag_idempotent_when_bit_absent() -> None:
    """Test remove_flag is idempotent when the bit is not present."""
    # Arrange
    original = QS.CATEGORIES
    expected = QS.CATEGORIES  # ACCOUNTS not present → no change

    # Act
    new_mask = original.remove_flag(QS.ACCOUNTS)

    # Assert
    assert (
        new_mask == expected
    ), "remove_flag should be idempotent when the bit is not present."


# ---------------------------
# remove_flags
# ---------------------------


def test_remove_flags_returns_new_mask_with_all_bits_cleared() -> None:
    """Test remove_flags returns immutable new mask with all specified bits cleared."""
    # Arrange
    original = QS.ACCOUNTS | QS.CATEGORIES | QS.TAGS
    to_remove = [QS.ACCOUNTS, QS.TAGS]
    expected = QS.CATEGORIES

    # Act
    new_mask = original.remove_flags(to_remove)

    # Assert
    assert (
        new_mask == expected
    ), "remove_flags should clear ALL provided bits on the returned mask."
    assert original == (
        QS.ACCOUNTS | QS.CATEGORIES | QS.TAGS
    ), "remove_flags must be immutable."
