# tests/controllers/test_qif_loader_protocol.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# System under test
import quicken_helper.controllers.qif_loader as ql

# Shared enums (use the same enum as the model uses)
from quicken_helper.data_model.interfaces import EnumClearedStatus

# ---- Minimal in-file stubs to isolate the loader contract --------------------


@dataclass
class _StubTxn:
    """Lightweight transaction stub matching the attributes the loader should pass through."""

    date: date
    amount: Decimal
    payee: str = ""
    memo: str = ""
    category: str = ""
    # Use a default_factory for Enum to avoid dataclass "mutable default" complaints
    cleared: EnumClearedStatus = field(
        default_factory=lambda: EnumClearedStatus.UNKNOWN
    )
    splits: list | None = None
    action: str | None = None


@dataclass
class _StubFile:
    """Lightweight file stub exposing the single attribute the loader consumes."""

    transactions: list[_StubTxn] = field(default_factory=lambda: [])


# ---- Tests -------------------------------------------------------------------


def test_loader_calls_parse_and_returns_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive: loader wires to parse function and returns the file's transactions list."""

    # Arrange
    called = {}

    def fake_parse_qif_unified(path: Path, encoding: str = "utf-8") -> _StubFile:
        called["args"] = (path, encoding)
        return _StubFile(
            transactions=[
                _StubTxn(
                    date=date(2025, 7, 4),
                    amount=Decimal("123.45"),
                    payee="Acme Co",
                    memo="Payment",
                    category="Utilities:Internet",
                    cleared=EnumClearedStatus.UNKNOWN,
                )
            ]
        )

    monkeypatch.setattr(ql, "parse_qif_unified_protocol", fake_parse_qif_unified)

    # Act
    out = ql.load_transactions_protocol(Path("X.qif"), encoding="latin-1")

    # Assert
    assert isinstance(out, list), "Loader must return a list of transactions"
    assert len(out) == 1, "Transactions from the parsed file should be returned as-is"
    assert called["args"] == (
        Path("X.qif"),
        "latin-1",
    ), "Path and encoding must be forwarded verbatim"
    t = out[0]
    assert isinstance(t, _StubTxn), "Loader should not adapt or wrap transactions"
    assert (t.date, t.amount, t.payee, t.memo, t.category, t.cleared) == (
        date(2025, 7, 4),
        Decimal("123.45"),
        "Acme Co",
        "Payment",
        "Utilities:Internet",
        EnumClearedStatus.UNKNOWN,
    )


def test_loader_propagates_parse_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative: loader must not swallow exceptions raised by the parser."""

    # Arrange
    def boom(*_a: object, **_kw: object) -> None:
        raise ValueError("bad qif")

    monkeypatch.setattr(ql, "parse_qif_unified_protocol", boom)

    # Act / Assert
    with pytest.raises(ValueError) as ei:
        ql.load_transactions_protocol(Path("bad.qif"))
    assert "bad qif" in str(ei.value)


def test_loader_does_not_mutate_transactions_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Positive: loader must pass through the original transaction objects without copying."""

    # Arrange
    tx = _StubTxn(date=date(2025, 1, 1), amount=Decimal("2.00"))

    def fake(*_a: object, **_kw: object) -> _StubFile:
        return _StubFile([tx])

    monkeypatch.setattr(ql, "parse_qif_unified_protocol", fake)

    # Act
    out = ql.load_transactions_protocol(Path("x.qif"))

    # Assert
    assert (
        out and out[0] is tx
    ), "Returned object should be the same instance produced by the parser"


def test_loader_returns_empty_list_when_no_transactions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edge: gracefully handle empty files by returning an empty list."""

    # Arrange
    monkeypatch.setattr(
        ql, "parse_qif_unified_protocol", lambda p, encoding="utf-8": _StubFile([])  # type: ignore[misc]
    )

    # Act
    out = ql.load_transactions_protocol(Path("empty.qif"))

    # Assert
    assert isinstance(out, list)
    assert out == []


def test_investment_action_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive: ensure loader preserves investment action fields unchanged."""

    # Arrange
    stub = _StubTxn(
        date=date(2025, 3, 15),
        amount=Decimal("1000"),
        action="Buy",  # Investment action should survive intact
    )
    monkeypatch.setattr(
        ql, "parse_qif_unified_protocol", lambda p, encoding="utf-8": _StubFile([stub])  # type: ignore[misc]
    )

    # Act
    out = ql.load_transactions_protocol(Path("inv.qif"))

    # Assert
    assert out[0].action == "Buy"  # type: ignore[attr-defined]


def test_splits_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """Positive: ensure loader preserves splits list without modification."""

    # Arrange
    splits = [{"category": "Food:Groceries", "amount": Decimal("50.00")}]
    stub = _StubTxn(date=date(2025, 2, 2), amount=Decimal("50.00"), splits=splits)
    monkeypatch.setattr(
        ql, "parse_qif_unified_protocol", lambda p, encoding="utf-8": _StubFile([stub])  # type: ignore[misc]
    )

    # Act
    out = ql.load_transactions_protocol(Path("splits.qif"))

    # Assert
    assert out[0].splits == splits  # type: ignore[attr-defined]
    assert (
        out[0].splits is splits  # type: ignore[attr-defined]
    ), "Identity check: loader must not copy or transform splits"


def test_load_transactions_with_stats_returns_stats(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Verify load_transactions_with_stats returns transactions and stats.

    Tests statistics collection during loading. Follows unit-test-policy.md.
    """
    # Arrange
    from dataclasses import dataclass

    @dataclass
    class FakeTxn:
        date: object = None
        amount: object = None
        payee: str = ""

    @dataclass
    class FakeFile:
        transactions: list = None

        def __post_init__(self):
            if self.transactions is None:
                self.transactions = [FakeTxn(), FakeTxn()]

    def fake_parse(path: Path, encoding: str = "utf-8") -> FakeFile:
        return FakeFile()

    import quicken_helper.controllers.qif_loader as ql

    monkeypatch.setattr(ql, "parse_qif_unified_protocol", fake_parse)

    qif_file = tmp_path / "test.qif"
    qif_file.write_text("!Type:Bank\nD01/01/2025\n^")

    # Act
    txns, stats = ql.load_transactions_with_stats(qif_file)

    # Assert
    assert len(txns) == 2, "Should load 2 transactions from fake"
    assert stats.lines_read > 0, "Should count lines read"
    assert stats.transactions_parsed == 2, "Should report 2 transactions parsed"
    assert not stats.has_errors, "Should have no errors"
    assert stats.success_rate == 100.0, "Should have 100% success rate"
