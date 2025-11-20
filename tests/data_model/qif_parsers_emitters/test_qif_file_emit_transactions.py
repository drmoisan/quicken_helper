# quicken_helper/tests/data_model/test_qif_file_emit_transactions.py
from __future__ import annotations

from quicken_helper.data_model import (
    ITransaction,
    QAccount,
    QuickenFile,
)


class _StubTxn(ITransaction):  # type: ignore[misc]
    """Minimal txn stub that records how emit_qif() was called and returns a body."""

    def __init__(self, account: QAccount, body: str) -> None:
        self.account = account
        self.body = body
        self.calls: list[tuple[bool, bool]] = []

    # Match the keyword-only call shape used by QifFile.emit_transactions
    def emit_qif(self, *, with_account: bool = False, with_type: bool = False) -> str:
        self.calls.append((with_account, with_type))
        parts: list[str] = []
        if with_account:
            parts.append(f"[A:{self.account.name}]")
        if with_type:
            parts.append("[T:TYPE]")
        parts.append(self.body)
        return "\n".join(parts)


class _NoneTxn:
    """Stub that returns None from emit_qif to exercise the fallback-to-empty-string path."""

    def __init__(self, account: QAccount) -> None:
        self.account = account
        self.calls: list[tuple[bool, bool]] = []

    def emit_qif(self, *, with_account: bool = False, with_type: bool = False) -> None:
        self.calls.append((with_account, with_type))
        return None


def test_emit_transactions_empty_returns_empty_string() -> None:
    """Verify that emit_transactions returns an empty string when there are no transactions."""
    # Arrange
    f = QuickenFile()
    f.transactions = []

    # Act
    out = f.emit_transactions()

    # Assert
    assert out == ""


def test_emit_transactions_first_in_account_emits_headers_then_suppresses_for_followups() -> (
    None
):
    """Verify that the first transaction in an account emits headers while subsequent transactions in the same account do not."""
    # Arrange
    f = QuickenFile()
    acct = QAccount(name="Checking", type="Bank", description="")
    t1 = _StubTxn(acct, "TXN1")  # type: ignore[abstract]
    t2 = _StubTxn(acct, "TXN2")  # type: ignore[abstract]
    f.transactions = [t1, t2]

    # Act
    out = f.emit_transactions()

    # Assert
    # First txn for an account -> with_account=True, with_type=True; subsequent -> both False
    assert t1.calls == [(True, True)]
    assert t2.calls == [(False, False)]
    # Joined with a single newline between txn texts
    assert out == "[A:Checking]\n[T:TYPE]\nTXN1\nTXN2"


def test_emit_transactions_reemits_headers_when_account_changes() -> None:
    """Verify that account and type headers are re-emitted when switching to a different account."""
    # Arrange
    f = QuickenFile()
    checking = QAccount(name="Checking", type="Bank", description="")
    savings = QAccount(name="Savings", type="Bank", description="")
    t1 = _StubTxn(checking, "C1")  # type: ignore[abstract]
    t2 = _StubTxn(checking, "C2")  # type: ignore[abstract]
    t3 = _StubTxn(savings, "S1")  # type: ignore[abstract]  # account change here should trigger headers again
    f.transactions = [t1, t2, t3]

    # Act
    out = f.emit_transactions()

    # Assert
    assert t1.calls == [(True, True)]
    assert t2.calls == [(False, False)]
    assert t3.calls == [(True, True)]  # account changed → headers again
    assert out == "[A:Checking]\n[T:TYPE]\nC1\nC2\n[A:Savings]\n[T:TYPE]\nS1"


def test_emit_transactions_coerces_none_to_empty_string() -> None:
    """Verify that a transaction returning None from emit_qif is coerced to an empty string."""
    # Arrange
    f = QuickenFile()
    acct = QAccount(name="Checking", type="Bank", description="")
    t1 = _StubTxn(acct, "TXN1")  # type: ignore[abstract]
    t2 = _NoneTxn(acct)  # returns None → should contribute empty text
    f.transactions = [t1, t2]  # type: ignore[list-item]

    # Act
    out = f.emit_transactions()

    # Assert
    assert t1.calls == [(True, True)]
    assert t2.calls == [(False, False)]
    # The None becomes "", so the join yields a trailing newline after the first body
    assert out == "[A:Checking]\n[T:TYPE]\nTXN1\n"
