"""
Centralized I/O operations for writing QIF and CSV files.

Separates I/O concerns from business logic and UI. All file write operations
should go through this module to ensure consistent error handling and logging.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


@dataclass
class ParseStats:
    """Statistics from file parsing operation."""

    lines_read: int = 0
    transactions_parsed: int = 0
    transactions_skipped: int = 0
    errors: list[str] = field(default_factory=list)

    def add_error(self, error: str) -> None:
        """Add an error message, keeping only the first 5."""
        if len(self.errors) < 5:
            self.errors.append(error)

    @property
    def has_errors(self) -> bool:
        """Check if there are any errors."""
        return len(self.errors) > 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate as percentage."""
        total = self.transactions_parsed + self.transactions_skipped
        if total == 0:
            return 100.0
        return (self.transactions_parsed / total) * 100.0


def write_qif(
    transactions: Sequence[Any],
    path: Path,
    *,
    encoding: str = "utf-8",
    newline: str = "\n",
) -> None:
    """
    Write transactions to QIF file.

    Args:
        transactions: Transactions to write (supports dicts, dataclasses,
                     or objects with to_dict() method)
        path: Output file path
        encoding: Text encoding (default UTF-8)
        newline: Line ending (default \\n, use \\r\\n for Windows CRLF)

    Raises:
        IOError: If file cannot be written
        TypeError: If transactions don't have a supported format
    """
    log.info("Writing %d transactions to QIF: %s", len(transactions), path)

    # Delegate to existing QIF writer
    from quicken_helper.legacy.qif_writer import write_qif as legacy_write_qif

    try:
        written = legacy_write_qif(
            path, transactions, encoding=encoding, newline=newline
        )
        log.debug("Successfully wrote %d transactions to QIF: %s", written, path)
    except Exception as e:
        log.exception("Failed to write QIF: %s", path)
        raise OSError(f"Failed to write QIF file: {e}") from e


def write_csv(
    transactions: Sequence[Any],
    path: Path,
    profile: str = "quicken-windows",
    *,
    encoding: str = "utf-8",
) -> None:
    """
    Write transactions to CSV file using specified profile.

    Args:
        transactions: Transactions to write (dicts or objects with to_dict())
        path: Output file path
        profile: CSV profile name ("quicken-windows" or "quicken-mac")
        encoding: Text encoding (default UTF-8)

    Raises:
        IOError: If file cannot be written
        ValueError: If profile unknown
        TypeError: If transactions don't have a supported format
    """
    log.info(
        "Writing %d transactions to CSV (%s): %s",
        len(transactions),
        profile,
        path,
    )

    # Convert transactions to dicts if needed
    txn_dicts: list[dict[str, Any]] = []
    for txn in transactions:
        if isinstance(txn, dict):
            txn_dicts.append(txn)
        elif hasattr(txn, "to_dict") and callable(txn.to_dict):
            txn_dicts.append(txn.to_dict())
        else:
            # Try using asdict for dataclasses
            from dataclasses import asdict, is_dataclass

            if is_dataclass(txn):
                txn_dicts.append(asdict(txn))
            else:
                raise TypeError(
                    f"Cannot convert transaction to dict: {type(txn).__name__}; "
                    "expected dict, dataclass, or object with to_dict() method"
                )

    # Delegate to CSV profile writers
    from quicken_helper.gui_viewers.csv_profiles import (
        write_csv_quicken_mac,
        write_csv_quicken_windows,
    )

    try:
        if profile == "quicken-windows":
            write_csv_quicken_windows(txn_dicts, path)
        elif profile == "quicken-mac":
            write_csv_quicken_mac(txn_dicts, path)
        else:
            raise ValueError(f"Unknown CSV profile: {profile}")

        log.debug("Successfully wrote CSV: %s", path)
    except ValueError:
        # Re-raise ValueError for unknown profile
        raise
    except Exception as e:
        log.exception("Failed to write CSV: %s", path)
        raise OSError(f"Failed to write CSV file: {e}") from e
