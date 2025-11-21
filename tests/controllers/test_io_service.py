"""
Tests for io_service module - centralized I/O operations.

These tests verify that write_qif and write_csv functions correctly
delegate to the underlying writers and handle errors appropriately.

Policy compliance:
- No filesystem I/O: All file operations are mocked
- Fast & deterministic: No external dependencies
- Isolation: Tests verify delegation and error handling without actual writes
"""

from __future__ import annotations

from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, mock_open, patch

import pytest

from quicken_helper.controllers.io_service import ParseStats, write_csv, write_qif

# Test fixtures and helpers


@dataclass
class MockTransaction:
    """Mock transaction for testing."""

    date: str
    payee: str
    amount: float
    category: str = ""
    memo: str = ""
    checknum: str = ""
    account: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "date": self.date,
            "payee": self.payee,
            "amount": self.amount,
            "category": self.category,
            "memo": self.memo,
            "checknum": self.checknum,
            "account": self.account,
        }


def _make_test_transaction(
    date: str = "2025-01-01", payee: str = "Test Payee", amount: float = 100.0
) -> MockTransaction:
    """Create a test transaction with default values."""
    return MockTransaction(
        date=date,
        payee=payee,
        amount=amount,
        category="Groceries",
        memo="Test memo",
    )


# Tests for write_qif


def test_write_qif_creates_valid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif delegates to legacy_write_qif correctly.

    Tests I/O service delegation without filesystem I/O. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", amount=100.0)
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer to track calls
    mock_writer = MagicMock(return_value=1)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)

    # Act
    write_qif([txn], out_file)

    # Assert
    mock_writer.assert_called_once()
    call_args = mock_writer.call_args
    assert call_args[0][0] == out_file, "Should pass path to writer"
    assert call_args[0][1] == [txn], "Should pass transactions to writer"
    assert call_args[1]["encoding"] == "utf-8", "Should use utf-8 encoding"


def test_write_qif_handles_dict_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif accepts dict-based transactions.

    Tests that the service handles legacy dict format. Follows unit-test-policy.md.
    """
    # Arrange
    txn_dict = {
        "date": "2025-01-01",
        "payee": "Test Store",
        "amount": 50.0,
        "category": "Shopping",
    }
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer
    mock_writer = MagicMock(return_value=1)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)

    # Act
    write_qif([txn_dict], out_file)

    # Assert
    mock_writer.assert_called_once()
    assert mock_writer.call_args[0][1] == [txn_dict], "Should pass dict transaction"


def test_write_qif_handles_protocol_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif accepts objects with to_dict() method.

    Tests protocol-based transaction support. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-02-15", payee="Protocol Test", amount=200.0)
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer
    mock_writer = MagicMock(return_value=1)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)

    # Act
    write_qif([txn], out_file)

    # Assert
    mock_writer.assert_called_once()
    assert mock_writer.call_args[0][1] == [txn], "Should pass protocol object"


def test_write_qif_multiple_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif handles multiple transactions.

    Tests batch writing capability. Follows unit-test-policy.md.
    """
    # Arrange
    txns = [
        _make_test_transaction(date="2025-01-01", payee="Store A", amount=100.0),
        _make_test_transaction(date="2025-01-02", payee="Store B", amount=200.0),
        _make_test_transaction(date="2025-01-03", payee="Store C", amount=300.0),
    ]
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer
    mock_writer = MagicMock(return_value=3)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)

    # Act
    write_qif(txns, out_file)

    # Assert
    mock_writer.assert_called_once()
    assert len(mock_writer.call_args[0][1]) == 3, "Should pass all 3 transactions"


def test_write_qif_with_encoding(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif respects encoding parameter.

    Tests encoding support for international characters. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(payee="Café français", amount=50.0)
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer
    mock_writer = MagicMock(return_value=1)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)

    # Act
    write_qif([txn], out_file, encoding="utf-8")

    # Assert
    mock_writer.assert_called_once()
    assert mock_writer.call_args[1]["encoding"] == "utf-8", "Should pass encoding parameter"


# Tests for write_csv


def test_write_csv_windows_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_csv delegates to write_csv_quicken_windows correctly.

    Tests CSV output with Quicken Windows format. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", payee="Test Store", amount=100.0)
    out_file = Path("/mock/output.csv")
    
    # Mock the CSV writer
    mock_writer = MagicMock()
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "write_csv_quicken_windows", mock_writer)

    # Act
    write_csv([txn], out_file, profile="quicken-windows")

    # Assert
    mock_writer.assert_called_once()
    call_args = mock_writer.call_args
    # First arg should be list of dicts
    assert isinstance(call_args[0][0], list), "Should pass list"
    assert isinstance(call_args[0][0][0], dict), "Should pass dicts"
    assert call_args[0][1] == out_file, "Should pass output path"


def test_write_csv_mac_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_csv delegates to write_csv_quicken_mac correctly.

    Tests CSV output with Quicken Mac format. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", payee="Test Store", amount=100.0)
    out_file = Path("/mock/output.csv")
    
    # Mock the CSV writer
    mock_writer = MagicMock()
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "write_csv_quicken_mac", mock_writer)

    # Act
    write_csv([txn], out_file, profile="quicken-mac")

    # Assert
    mock_writer.assert_called_once()
    assert mock_writer.call_args[0][1] == out_file, "Should pass output path"


def test_write_csv_unknown_profile_raises() -> None:
    """
    Verify write_csv raises ValueError for unknown profile.

    Tests error handling for invalid profile. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", amount=100.0)
    out_file = Path("/mock/output.csv")

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown CSV profile"):
        write_csv([txn], out_file, profile="unknown-profile")


def test_write_csv_handles_dict_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_csv accepts dict-based transactions.

    Tests that the service handles legacy dict format. Follows unit-test-policy.md.
    """
    # Arrange
    txn_dict = {
        "date": "2025-01-01",
        "payee": "Test Store",
        "amount": 50.0,
        "category": "Shopping",
        "memo": "Test purchase",
    }
    out_file = Path("/mock/output.csv")
    
    # Mock the CSV writer
    mock_writer = MagicMock()
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "write_csv_quicken_windows", mock_writer)

    # Act
    write_csv([txn_dict], out_file, profile="quicken-windows")

    # Assert
    mock_writer.assert_called_once()
    passed_dict = mock_writer.call_args[0][0][0]
    assert passed_dict["payee"] == "Test Store", "Should pass dict with payee"


def test_write_csv_handles_protocol_objects(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_csv accepts objects with to_dict() method.

    Tests protocol-based transaction support. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-02-15", payee="Protocol CSV", amount=200.0)
    out_file = Path("/mock/output.csv")
    
    # Mock the CSV writer
    mock_writer = MagicMock()
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "write_csv_quicken_windows", mock_writer)

    # Act
    write_csv([txn], out_file, profile="quicken-windows")

    # Assert
    mock_writer.assert_called_once()
    passed_dict = mock_writer.call_args[0][0][0]
    assert passed_dict["payee"] == "Protocol CSV", "Should convert to dict with payee"


def test_write_csv_multiple_transactions(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_csv handles multiple transactions.

    Tests batch writing capability for CSV. Follows unit-test-policy.md.
    """
    # Arrange
    txns = [
        _make_test_transaction(date="2025-01-01", payee="Store A", amount=100.0),
        _make_test_transaction(date="2025-01-02", payee="Store B", amount=200.0),
        _make_test_transaction(date="2025-01-03", payee="Store C", amount=300.0),
    ]
    out_file = Path("/mock/output.csv")
    
    # Mock the CSV writer
    mock_writer = MagicMock()
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "write_csv_quicken_windows", mock_writer)

    # Act
    write_csv(txns, out_file, profile="quicken-windows")

    # Assert
    mock_writer.assert_called_once()
    passed_dicts = mock_writer.call_args[0][0]
    assert len(passed_dicts) == 3, "Should pass all 3 transactions as dicts"


def test_write_csv_invalid_transaction_type_raises() -> None:
    """
    Verify write_csv raises TypeError for unsupported transaction type.

    Tests error handling for invalid input. Follows unit-test-policy.md.
    """
    # Arrange
    invalid_txn = "not a transaction"  # String is not a valid transaction
    out_file = Path("/mock/output.csv")

    # Act & Assert
    with pytest.raises(TypeError, match="Cannot convert transaction to dict"):
        write_csv([invalid_txn], out_file, profile="quicken-windows")


# Error handling tests


def test_write_qif_invalid_transaction_type_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif raises error for unsupported transaction type.

    Tests error handling for invalid input. Follows unit-test-policy.md.
    """
    # Arrange
    invalid_txn = 12345  # Integer is not a valid transaction
    out_file = Path("/mock/output.qif")
    
    # Mock the legacy writer to raise TypeError
    def mock_writer_raises(*args: object, **kwargs: object) -> int:
        raise TypeError("Invalid transaction type")
    
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer_raises)

    # Act & Assert
    with pytest.raises(OSError, match="Failed to write QIF file"):
        write_qif([invalid_txn], out_file)


def test_write_qif_invalid_path_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Verify write_qif raises OSError for filesystem issues.

    Tests error handling for I/O errors. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction()
    invalid_path = Path("/nonexistent_root_dir_12345/subdir/output.qif")
    
    # Mock the legacy writer to raise IOError
    def mock_writer_raises(*args: object, **kwargs: object) -> int:
        raise IOError("Permission denied")
    
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer_raises)

    # Act & Assert
    with pytest.raises(OSError, match="Failed to write QIF file"):
        write_qif([txn], invalid_path)


# Tests for ParseStats


def test_parse_stats_default_values() -> None:
    """
    Verify ParseStats initializes with default values.

    Tests dataclass initialization. Follows unit-test-policy.md.
    """
    # Arrange & Act
    stats = ParseStats()

    # Assert
    assert stats.lines_read == 0, "Should default to 0 lines"
    assert stats.transactions_parsed == 0, "Should default to 0 parsed"
    assert stats.transactions_skipped == 0, "Should default to 0 skipped"
    assert stats.errors == [], "Should default to empty error list"
    assert not stats.has_errors, "Should have no errors initially"


def test_parse_stats_add_error() -> None:
    """
    Verify ParseStats.add_error adds errors up to limit.

    Tests error collection with size limit. Follows unit-test-policy.md.
    """
    # Arrange
    stats = ParseStats()

    # Act - add 6 errors (limit is 5)
    for i in range(6):
        stats.add_error(f"Error {i}")

    # Assert
    assert len(stats.errors) == 5, "Should keep only first 5 errors"
    assert stats.errors[0] == "Error 0", "Should keep first error"
    assert stats.errors[4] == "Error 4", "Should keep fifth error"
    assert stats.has_errors, "Should indicate errors exist"


def test_parse_stats_success_rate_all_parsed() -> None:
    """
    Verify ParseStats.success_rate calculates correctly for 100% success.

    Tests success rate calculation. Follows unit-test-policy.md.
    """
    # Arrange
    stats = ParseStats(transactions_parsed=10, transactions_skipped=0)

    # Act
    rate = stats.success_rate

    # Assert
    assert rate == 100.0, "Should be 100% when no transactions skipped"


def test_parse_stats_success_rate_partial() -> None:
    """
    Verify ParseStats.success_rate calculates correctly for partial success.

    Tests success rate calculation with failures. Follows unit-test-policy.md.
    """
    # Arrange
    stats = ParseStats(transactions_parsed=7, transactions_skipped=3)

    # Act
    rate = stats.success_rate

    # Assert
    assert rate == 70.0, "Should be 70% when 7 of 10 parsed"


def test_parse_stats_success_rate_empty() -> None:
    """
    Verify ParseStats.success_rate returns 100% for empty input.

    Tests edge case of no transactions. Follows unit-test-policy.md.
    """
    # Arrange
    stats = ParseStats(transactions_parsed=0, transactions_skipped=0)

    # Act
    rate = stats.success_rate

    # Assert
    assert rate == 100.0, "Should be 100% when no transactions at all"
