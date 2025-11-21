"""
Tests for io_service module - centralized I/O operations.

These tests verify that write_qif and write_csv functions correctly
delegate to the underlying writers and handle errors appropriately.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from quicken_helper.controllers.io_service import write_csv, write_qif

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


def test_write_qif_creates_valid_file(tmp_path: Path) -> None:
    """
    Verify write_qif creates valid QIF file from transactions.

    Tests I/O service write operation. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", amount=100.0)
    out_file = tmp_path / "output.qif"

    # Act
    write_qif([txn], out_file)

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "!Type:Bank" in content or "D" in content, "Should contain QIF markers"
    assert "^" in content, "Should contain record separator"


def test_write_qif_handles_dict_transactions(tmp_path: Path) -> None:
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
    out_file = tmp_path / "output.qif"

    # Act
    write_qif([txn_dict], out_file)

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert len(content) > 0, "Should write content"


def test_write_qif_handles_protocol_objects(tmp_path: Path) -> None:
    """
    Verify write_qif accepts objects with to_dict() method.

    Tests protocol-based transaction support. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-02-15", payee="Protocol Test", amount=200.0)
    out_file = tmp_path / "output.qif"

    # Act
    write_qif([txn], out_file)

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert len(content) > 0, "Should write content"


def test_write_qif_multiple_transactions(tmp_path: Path) -> None:
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
    out_file = tmp_path / "output.qif"

    # Act
    write_qif(txns, out_file)

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    # Each transaction should have a record separator
    separator_count = content.count("^")
    assert separator_count >= len(txns), f"Should have {len(txns)} or more separators"


def test_write_qif_with_encoding(tmp_path: Path) -> None:
    """
    Verify write_qif respects encoding parameter.

    Tests encoding support for international characters. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(payee="Café français", amount=50.0)
    out_file = tmp_path / "output.qif"

    # Act
    write_qif([txn], out_file, encoding="utf-8")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text(encoding="utf-8")
    assert len(content) > 0, "Should write content"


# Tests for write_csv


def test_write_csv_windows_profile(tmp_path: Path) -> None:
    """
    Verify write_csv creates valid CSV with Windows profile.

    Tests CSV output with Quicken Windows format. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", payee="Test Store", amount=100.0)
    out_file = tmp_path / "output.csv"

    # Act
    write_csv([txn], out_file, profile="quicken-windows")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "Date" in content, "Should have Date header"
    assert "Payee" in content, "Should have Payee header"
    assert "Amount" in content, "Should have Amount header"
    # Check for some transaction data
    assert (
        "Test Store" in content or "100" in content
    ), "Should contain transaction data"


def test_write_csv_mac_profile(tmp_path: Path) -> None:
    """
    Verify write_csv creates valid CSV with Mac profile.

    Tests CSV output with Quicken Mac format. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", payee="Test Store", amount=100.0)
    out_file = tmp_path / "output.csv"

    # Act
    write_csv([txn], out_file, profile="quicken-mac")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "Date" in content, "Should have Date header"
    assert "Description" in content, "Should have Description header (Mac format)"
    assert "Amount" in content, "Should have Amount header"


def test_write_csv_unknown_profile_raises(tmp_path: Path) -> None:
    """
    Verify write_csv raises ValueError for unknown profile.

    Tests error handling for invalid profile. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-01-01", amount=100.0)
    out_file = tmp_path / "output.csv"

    # Act & Assert
    with pytest.raises(ValueError, match="Unknown CSV profile"):
        write_csv([txn], out_file, profile="unknown-profile")


def test_write_csv_handles_dict_transactions(tmp_path: Path) -> None:
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
    out_file = tmp_path / "output.csv"

    # Act
    write_csv([txn_dict], out_file, profile="quicken-windows")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "Test Store" in content, "Should contain payee"


def test_write_csv_handles_protocol_objects(tmp_path: Path) -> None:
    """
    Verify write_csv accepts objects with to_dict() method.

    Tests protocol-based transaction support. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction(date="2025-02-15", payee="Protocol CSV", amount=200.0)
    out_file = tmp_path / "output.csv"

    # Act
    write_csv([txn], out_file, profile="quicken-windows")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "Protocol CSV" in content, "Should contain payee"


def test_write_csv_multiple_transactions(tmp_path: Path) -> None:
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
    out_file = tmp_path / "output.csv"

    # Act
    write_csv(txns, out_file, profile="quicken-windows")

    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    lines = content.strip().split("\n")
    # Header + 3 transactions
    assert (
        len(lines) >= 4
    ), f"Should have at least 4 lines (header + 3 txns), got {len(lines)}"


def test_write_csv_invalid_transaction_type_raises(tmp_path: Path) -> None:
    """
    Verify write_csv raises TypeError for unsupported transaction type.

    Tests error handling for invalid input. Follows unit-test-policy.md.
    """
    # Arrange
    invalid_txn = "not a transaction"  # String is not a valid transaction
    out_file = tmp_path / "output.csv"

    # Act & Assert
    with pytest.raises(TypeError, match="Cannot convert transaction to dict"):
        write_csv([invalid_txn], out_file, profile="quicken-windows")


# Error handling tests


def test_write_qif_invalid_transaction_type_raises(tmp_path: Path) -> None:
    """
    Verify write_qif raises TypeError for unsupported transaction type.

    Tests error handling for invalid input. Follows unit-test-policy.md.
    """
    # Arrange
    invalid_txn = 12345  # Integer is not a valid transaction
    out_file = tmp_path / "output.qif"

    # Act & Assert
    with pytest.raises((TypeError, OSError)):
        write_qif([invalid_txn], out_file)


def test_write_qif_invalid_path_raises(tmp_path: Path) -> None:
    """
    Verify write_qif raises OSError for invalid path.

    Tests error handling for filesystem issues. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_test_transaction()
    # Create a path that cannot be written (directory doesn't exist and won't be created)
    invalid_path = Path("/nonexistent_root_dir_12345/subdir/output.qif")

    # Act & Assert
    # The function will try to create parent dirs, but /nonexistent_root should fail
    with pytest.raises(OSError):
        write_qif([txn], invalid_path)
