from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

import quicken_helper.controllers.match_excel as mx
from quicken_helper.data_model.excel.excel_row import ExcelRow

# --------------------------- load_excel_rows ----------------------------------


def test_load_excel_rows_parses_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    """load_excel_rows: parses a DataFrame into typed ExcelRow objects, preserving
    per-row index (idx), grouping IDs (TxnID), and converting Amount to Decimal.
    """
    df = pd.DataFrame(
        {
            "TxnID": ["G1", "G1", "G2"],
            "Date": [date(2025, 8, 10), date(2025, 8, 10), date(2025, 8, 9)],
            "Amount": ["-10.00", "-20.00", "-7.50"],
            "Item": ["i1", "i2", "j1"],
            "Canonical MECE Category": ["C1", "C2", "C3"],
            "Categorization Rationale": ["r1", "r2", "r3"],
        }
    )
    monkeypatch.setattr(pd, "read_excel", lambda p: df)  # type: ignore[misc]

    rows = mx.load_excel_rows(Path("dummy.xlsx"))

    assert [type(r) for r in rows] == [ExcelRow] * 3
    assert (
        rows[0].txn_id == "G1"
        and rows[0].idx == 0
        and rows[0].amount == Decimal("-10.00")
    )
    assert rows[1].txn_id == "G1" and rows[2].txn_id == "G2"


def test_load_excel_rows_missing_columns_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """load_excel_rows: raises a ValueError if required columns are absent."""
    df = pd.DataFrame({"TxnID": ["X"], "Date": [date(2025, 8, 10)]})
    monkeypatch.setattr(pd, "read_excel", lambda p: df)  # type: ignore[misc]

    with pytest.raises(ValueError) as ei:
        mx.load_excel_rows(Path("missing.xlsx"))
    assert "missing columns" in str(ei.value).lower()


# --------------------------- group_excel_rows ---------------------------------


def test_group_excel_rows_groups_and_sorts() -> None:
    """group_excel_rows: groups rows by TxnID, sums total_amount, uses the earliest
    date as the group date, sorts groups by (date, gid), and preserves row order within groups.
    """
    rows = [
        ExcelRow(
            idx=1,
            txn_id="B",
            date=date(2025, 8, 11),
            amount=Decimal("-2.00"),
            memo="b2",
            category="C",
            rationale="r",
        ),
        ExcelRow(
            idx=0,
            txn_id="A",
            date=date(2025, 8, 10),
            amount=Decimal("-1.00"),
            memo="a1",
            category="C",
            rationale="r",
        ),
        ExcelRow(
            idx=2,
            txn_id="B",
            date=date(2025, 8, 12),
            amount=Decimal("-3.00"),
            memo="b3",
            category="C",
            rationale="r",
        ),
    ]
    groups = mx.group_excel_rows(rows)

    assert [g.gid for g in groups] == ["A", "B"]
    gA, gB = groups
    assert gA.total_amount == Decimal("-1.00") and gA.date == date(2025, 8, 10)
    assert gB.total_amount == Decimal("-5.00") and gB.date == date(2025, 8, 11)
    assert [r.idx for r in gB.rows] == [1, 2]


# ----------------------------- _txn_amount ------------------------------------


def test__txn_amount_prefers_splits_sum_over_txn_amount() -> None:
    """_txn_amount: if splits exist, returns the sum of split amounts (ignores txn-level amount)."""
    t = {"amount": "-999.99", "splits": [{"amount": "-1.00"}, {"amount": "-2.00"}]}
    assert mx._txn_amount(t) == Decimal("-3.00")  # type: ignore[reportPrivateUsage]


def test__txn_amount_falls_back_to_txn_amount_when_no_splits() -> None:
    """_txn_amount: if no splits, returns the transaction-level amount."""
    t: dict[str, object] = {"amount": "-12.34", "splits": []}
    assert mx._txn_amount(t) == Decimal("-12.34")  # type: ignore[reportPrivateUsage,arg-type]


# --------------------------- _flatten_qif_txns --------------------------------


def test_flatten_qif_txns_includes_split_views_and_whole_txn_and_skips_bad_split_amounts() -> (
    None
):
    """_flatten_qif_txns: produces a flat list of views for (valid) splits and for unsplit
    transactions, skipping any split with a non-numeric amount and any non-transaction input.
    """
    txns = [
        # txn 0: with splits (one bad amount to be skipped)
        {
            "date": "2025-08-10",
            "payee": "P0",
            "memo": "M0",
            "category": "C0",
            "splits": [
                {"amount": "-1.00", "memo": "s1", "category": "S1"},
                {"amount": "XYZ", "memo": "bad", "category": "BAD"},
                {"amount": "-2.00", "memo": "s2", "category": "S2"},
            ],
        },
        # txn 1: no splits, use txn amount
        {
            "date": "2025-08-11",
            "payee": "P1",
            "memo": "M1",
            "category": "C1",
            "amount": "-5.50",
        },
        # txn 2: not a transaction (bad date) → dropped
        {"date": "not-a-date", "amount": "-1.00"},
    ]
    views = mx._flatten_qif_txns(txns)  # type: ignore[reportPrivateUsage]

    assert len(views) == 3
    keys = [(v.key.txn_index, v.key.split_index) for v in views]
    assert keys == [(0, 0), (0, 2), (1, None)]
    amts = [v.amount for v in views]
    assert amts == [Decimal("-1.00"), Decimal("-2.00"), Decimal("-5.50")]
    cats = [v.category for v in views]
    assert cats == ["S1", "S2", "C1"]


# ---------------------- extract_qif/excel_categories --------------------------


def test_extract_qif_categories_dedup_and_sort() -> None:
    """extract_qif_categories: gathers categories from both txn-level and split-level,
    normalizes case/whitespace, de-duplicates, and returns a sorted list.
    """
    txns = [
        {
            "category": "Food:Groceries",
            "splits": [{"category": "Home:Repairs"}, {"category": "food:groceries"}],
        },
        {
            "category": "  ",
            "splits": [{"category": ""}, {"category": "Utilities: Internet"}],
        },
    ]
    cats = mx.extract_qif_categories(txns)
    assert cats == ["Food:Groceries", "Home:Repairs", "Utilities: Internet"]


def test_extract_excel_categories_reads_and_dedups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """extract_excel_categories: reads 'Canonical MECE Category' from Excel, strips,
    de-duplicates ignoring case, and returns sorted non-empty values.
    """
    df = pd.DataFrame(
        {"Canonical MECE Category": ["Groceries", "groceries", "Restaurants", ""]}
    )
    monkeypatch.setattr(pd, "read_excel", lambda p: df)  # type: ignore[misc]

    out = mx.extract_excel_categories(Path("cats.xlsx"))
    assert out == ["Groceries", "Restaurants"]


# --------------------------------- _ratio -------------------------------------


def test__ratio_is_case_insensitive_and_exact_for_equal_strings() -> None:
    """_ratio: returns 1.0 for equal strings ignoring case."""
    assert mx._ratio("Food:Groceries", "food:groceries") == 1.0  # type: ignore[reportPrivateUsage]


# ---------------------------- fuzzy_autopairs ---------------------------------


def test_fuzzy_autopairs_threshold_and_one_to_one() -> None:
    """fuzzy_autopairs: with threshold=0.80, 'Food:Restaurants' ↔ 'Restaurants' meets the
    threshold (≈0.8148) and matches; 'Food:Groceries' ↔ 'Groceries' is below threshold, so both
    remain unmatched. Also confirms 'Other' remains unmatched.
    """
    pairs, uq, ue = mx.fuzzy_autopairs(
        qif_cats=["Food:Groceries", "Food:Restaurants"],
        excel_cats=["Groceries", "Restaurants", "Other"],
        threshold=0.80,
    )
    match = next(
        (p for p in pairs if p[0] == "Food:Restaurants" and p[1] == "Restaurants"), None
    )
    assert match is not None and match[2] >= 0.80

    assert "Food:Groceries" in uq
    assert "Groceries" in ue
    assert "Other" in ue


def test_fuzzy_autopairs_deterministic_tie_breaks_by_alpha() -> None:
    """fuzzy_autopairs: when multiple pairs have identical scores, selection is deterministic
    (stable) by sorting key (e.g., (-score, qif_name, excel_name)); hence Ab↔Ab precedes Ac↔Ac.
    """
    pairs, _, _ = mx.fuzzy_autopairs(
        qif_cats=["Ab", "Ac"],
        excel_cats=["Ab", "Ac"],
        threshold=0.5,
    )
    assert pairs[0][:2] == ("Ab", "Ab")
    assert pairs[1][:2] == ("Ac", "Ac")


# ------------------------ build_matched_only_txns -----------------------------


def test_build_matched_only_txns_returns_matched_bank_transactions() -> None:
    """
    Verify build_matched_only_txns returns only bank txns with matches.

    Tests positive flow with valid matches using protocol-based MatchSession.
    Follows unit-test-policy.md.
    """
    from quicken_helper.controllers.match_session import MatchSession
    from quicken_helper.data_model.q_wrapper.q_transaction import QTransaction

    # Arrange: Create bank transactions
    bank_txn1 = QTransaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Test Payee 1",
        memo="Test Memo 1",
    )
    bank_txn2 = QTransaction(
        date=date(2025, 1, 2),
        amount=Decimal("200.00"),
        payee="Test Payee 2",
        memo="Test Memo 2",
    )
    bank_txn3 = QTransaction(
        date=date(2025, 1, 3),
        amount=Decimal("300.00"),
        payee="Test Payee 3",
        memo="Test Memo 3",
    )

    # Create Excel transactions (match txn1 and txn3, not txn2)
    excel_txn1 = QTransaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Excel Payee 1",
    )
    excel_txn2 = QTransaction(
        date=date(2025, 1, 3),
        amount=Decimal("300.00"),
        payee="Excel Payee 2",
    )

    # Create session and manually add pairs
    session = MatchSession(
        [bank_txn1, bank_txn2, bank_txn3],
        [excel_txn1, excel_txn2],
    )
    session.manual_match(0, 0)  # bank_txn1 <-> excel_txn1
    session.manual_match(2, 1)  # bank_txn3 <-> excel_txn2

    # Act
    result = mx.build_matched_only_txns(session)

    # Assert
    assert len(result) == 2, "Should return 2 matched transactions"
    assert result[0] is bank_txn1, "First matched txn should be bank_txn1"
    assert result[1] is bank_txn3, "Second matched txn should be bank_txn3"


def test_build_matched_only_txns_preserves_order() -> None:
    """Verify matched transactions returned in original bank_txns order."""
    from quicken_helper.controllers.match_session import MatchSession
    from quicken_helper.data_model.q_wrapper.q_transaction import QTransaction

    # Arrange: Create 5 bank transactions
    bank_txns = [
        QTransaction(
            date=date(2025, 1, i),
            amount=Decimal(f"{i * 100}.00"),
            payee=f"Payee {i}",
        )
        for i in range(1, 6)
    ]

    # Create 2 Excel transactions
    excel_txns = [
        QTransaction(
            date=date(2025, 1, i),
            amount=Decimal(f"{i * 100}.00"),
            payee=f"Excel {i}",
        )
        for i in [2, 4]
    ]

    # Create session and match out of order (txn[3] then txn[1])
    session = MatchSession(bank_txns, excel_txns)
    session.manual_match(3, 1)  # bank_txns[3] <-> excel_txns[1]
    session.manual_match(1, 0)  # bank_txns[1] <-> excel_txns[0]

    # Act
    result = mx.build_matched_only_txns(session)

    # Assert: Should preserve bank_txns order (index 1, then 3)
    assert len(result) == 2
    assert result[0] is bank_txns[1], "First result should be bank_txns[1]"
    assert result[1] is bank_txns[3], "Second result should be bank_txns[3]"


def test_build_matched_only_txns_empty_pairs() -> None:
    """Verify empty list returned when no matches exist."""
    from quicken_helper.controllers.match_session import MatchSession
    from quicken_helper.data_model.q_wrapper.q_transaction import QTransaction

    # Arrange
    bank_txn = QTransaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Test Payee",
    )
    excel_txn = QTransaction(
        date=date(2025, 1, 2),
        amount=Decimal("200.00"),
        payee="Excel Payee",
    )

    session = MatchSession([bank_txn], [excel_txn])
    # Don't create any matches

    # Act
    result = mx.build_matched_only_txns(session)

    # Assert
    assert result == [], "Should return empty list when no pairs"


def test_build_matched_only_txns_does_not_mutate_session() -> None:
    """Verify function is pure and does not modify session."""
    from quicken_helper.controllers.match_session import MatchSession
    from quicken_helper.data_model.q_wrapper.q_transaction import QTransaction

    # Arrange
    bank_txn = QTransaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Test Payee",
    )
    excel_txn = QTransaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Excel Payee",
    )

    session = MatchSession([bank_txn], [excel_txn])
    session.manual_match(0, 0)

    original_bank_count = len(session.bank_txns)
    original_pair_count = len(session.pairs)

    # Act
    mx.build_matched_only_txns(session)

    # Assert
    assert len(session.bank_txns) == original_bank_count, "Should not mutate bank_txns"
    assert len(session.pairs) == original_pair_count, "Should not mutate pairs"


# PREVIOUS VERSION OF THE FILE (kept for reference; not executed):
# from __future__ import annotations
#
# from datetime import date
# from decimal import Decimal
# from pathlib import Path
#
# import pandas as pd
# import pytest
#
# import quicken_helper.match_excel as mx
# from quicken_helper.excel_row import ExcelRow
# from quicken_helper.excel_txn_group import ExcelTxnGroup
# from quicken_helper.qif_item_key import QIFItemKey
#
#
# # --------------------------- load_excel_rows ----------------------------------
#
# def test_load_excel_rows_parses_rows(monkeypatch):
#     # Arrange: construct a DataFrame with required columns
#     df = pd.DataFrame({
#         "TxnID": ["G1", "G1", "G2"],
#         "Date": [date(2025, 8, 10), date(2025, 8, 10), date(2025, 8, 9)],  # already dates
#         "Amount": ["-10.00", "-20.00", "-7.50"],  # strings are OK
#         "Item": ["i1", "i2", "j1"],
#         "Canonical MECE Category": ["C1", "C2", "C3"],
#         "Categorization Rationale": ["r1", "r2", "r3"],
#     })
#     monkeypatch.setattr(pd, "read_excel", lambda p: df)
#
#     # Act
#     rows = mx.load_excel_rows(Path("dummy.xlsx"))
#
#     # Assert
#     assert [type(r) for r in rows] == [ExcelRow] * 3
#     assert rows[0].txn_id == "G1" and rows[0].idx == 0 and rows[0].amount == Decimal("-10.00")
#     assert rows[1].txn_id == "G1" and rows[2].txn_id == "G2"
#
#
# def test_load_excel_rows_missing_columns_raises(monkeypatch):
#     df = pd.DataFrame({"TxnID": ["X"], "Date": [date(2025, 8, 10)]})
#     monkeypatch.setattr(pd, "read_excel", lambda p: df)
#     with pytest.raises(ValueError) as ei:
#         mx.load_excel_rows(Path("missing.xlsx"))
#     assert "missing columns" in str(ei.value).lower()
#
#
# # --------------------------- group_excel_rows ---------------------------------
#
# def test_group_excel_rows_groups_and_sorts():
#     rows = [
#         ExcelRow(idx=1, txn_id="B", date=date(2025, 8, 11), amount=Decimal("-2.00"), item="b2", category="C", rationale="r"),
#         ExcelRow(idx=0, txn_id="A", date=date(2025, 8, 10), amount=Decimal("-1.00"), item="a1", category="C", rationale="r"),
#         ExcelRow(idx=2, txn_id="B", date=date(2025, 8, 12), amount=Decimal("-3.00"), item="b3", category="C", rationale="r"),
#     ]
#     groups = mx.group_excel_rows(rows)
#     assert [g.gid for g in groups] == ["A", "B"]  # by earliest date then gid
#     gA, gB = groups
#     assert gA.total_amount == Decimal("-1.00") and gA.date == date(2025, 8, 10)
#     assert gB.total_amount == Decimal("-5.00") and gB.date == date(2025, 8, 11)
#     # rows are ordered by original idx within each group
#     assert [r.idx for r in gB.rows] == [1, 2]
#
#
# # ----------------------------- _txn_amount ------------------------------------
#
# def test__txn_amount_prefers_splits_sum_over_txn_amount():
#     t = {"amount": "-999.99", "splits": [{"amount": "-1.00"}, {"amount": "-2.00"}]}
#     assert mx._txn_amount(t) == Decimal("-3.00")
#
# def test__txn_amount_falls_back_to_txn_amount_when_no_splits():
#     t = {"amount": "-12.34", "splits": []}
#     assert mx._txn_amount(t) == Decimal("-12.34")
#
#
# # --------------------------- _flatten_qif_txns --------------------------------
#
# def test_flatten_qif_txns_includes_split_views_and_whole_txn_and_skips_bad_split_amounts():
#     txns = [
#         # txn 0: with splits (one bad amount to be skipped)
#         {"date": "2025-08-10", "payee": "P0", "memo": "M0", "category": "C0",
#          "splits": [{"amount": "-1.00", "memo": "s1", "category": "S1"},
#                     {"amount": "XYZ", "memo": "bad", "category": "BAD"},
#                     {"amount": "-2.00", "memo": "s2", "category": "S2"}]},
#         # txn 1: no splits, use txn amount
#         {"date": "2025-08-11", "payee": "P1", "memo": "M1", "category": "C1", "amount": "-5.50"},
#         # txn 2: not a transaction (bad date) → dropped
#         {"date": "not-a-date", "amount": "-1.00"},
#     ]
#     views = mx._flatten_qif_txns(txns)
#     # Expect 3 views: two splits from txn 0 (indices 0 and 2), and whole txn 1
#     assert len(views) == 3
#     # keys
#     keys = [(v.key.txn_index, v.key.split_index) for v in views]
#     assert keys == [(0, 0), (0, 2), (1, None)]
#     # amounts
#     amts = [v.amount for v in views]
#     assert amts == [Decimal("-1.00"), Decimal("-2.00"), Decimal("-5.50")]
#     # categories: split-specific for split views; txn-level for whole txn
#     cats = [v.category for v in views]
#     assert cats == ["S1", "S2", "C1"]
#
#
# # ---------------------- extract_qif/excel_categories --------------------------
#
# def test_extract_qif_categories_dedup_and_sort():
#     txns = [
#         {"category": "Food:Groceries", "splits": [{"category": "Home:Repairs"}, {"category": "food:groceries"}]},
#         {"category": "  ", "splits": [{"category": ""}, {"category": "Utilities: Internet"}]},
#     ]
#     cats = mx.extract_qif_categories(txns)
#     assert cats == ["Food:Groceries", "Home:Repairs", "Utilities: Internet"]
#
# def test_extract_excel_categories_reads_and_dedups(monkeypatch):
#     df = pd.DataFrame({"Canonical MECE Category": ["Groceries", "groceries", "Restaurants", ""]})
#     monkeypatch.setattr(pd, "read_excel", lambda p: df)
#     out = mx.extract_excel_categories(Path("cats.xlsx"))
#     assert out == ["Groceries", "Restaurants"]
#
#
# # --------------------------------- _ratio -------------------------------------
#
# def test__ratio_is_case_insensitive_and_exact_for_equal_strings():
#     assert mx._ratio("Food:Groceries", "food:groceries") == 1.0
#
#
# # ---------------------------- fuzzy_autopairs ---------------------------------
#
# def test_fuzzy_autopairs_threshold_and_one_to_one():
#     pairs, uq, ue = mx.fuzzy_autopairs(
#         qif_cats=["Food:Groceries", "Food:Restaurants"],
#         excel_cats=["Groceries", "Restaurants", "Other"],
#         threshold=0.80,
#     )
#     # Exact matches should be picked; 'Other' remains unmatched
#     assert ("Food:Groceries", "Groceries", 1.0) in pairs
#     assert ("Food:Restaurants", "Restaurants", 1.0) in pairs
#     assert "Other" in ue and "Food:Groceries" not in uq and "Food:Restaurants" not in uq
#
# def test_fuzzy_autopairs_deterministic_tie_breaks_by_alpha():
#     # Construct two equal-score candidates and verify deterministic order/tie-break.
#     pairs, _, _ = mx.fuzzy_autopairs(
#         qif_cats=["Ab", "Ac"],
#         excel_cats=["Ab", "Ac"],
#         threshold=0.5,
#     )
#     # Highest ratios are 1.0 for (Ab,Ab) and (Ac,Ac); greedy picks by (-score, q, e)
#     assert pairs[0][:2] == ("Ab", "Ab")
#     assert pairs[1][:2] == ("Ac", "Ac")
#
#
# # ------------------------ build_matched_only_txns -----------------------------
#
# class _FakeSessionGroupMode:
#     def __init__(self, txns, matched_txn_indices):
#         self.txns = txns
#         self.excel_groups = [ExcelTxnGroup(gid="G", date=date(2025, 8, 10),
#                                            total_amount=Decimal("0"), rows=tuple())]
#         # map whole-txn keys to group index 0
#         self.qif_to_excel_group = {QIFItemKey(ti, None): 0 for ti in matched_txn_indices}
#
# class _FakeSessionLegacyMode:
#     def __init__(self, txns, matched_keys):
#         self.txns = txns
#         self.excel_groups = None
#         # emulate row-mode mapping: keys (txn_index, split_index or None) -> row index
#         self.qif_to_excel_row = {k: 0 for k in matched_keys}
#
# def test_build_matched_only_txns_group_mode_includes_only_matched_txns():
#     txns = [
#         {"date": "2025-08-10", "amount": "-1.00"},
#         {"date": "2025-08-11", "amount": "-2.00"},
#     ]
#     session = _FakeSessionGroupMode(txns, matched_txn_indices=[0])
#     out = mx.build_matched_only_txns(session)
#     assert len(out) == 1 and out[0]["amount"] == "-1.00"
#
# def test_build_matched_only_txns_legacy_mode_filters_splits_and_includes_whole_txn():
#     txns = [
#         # txn 0 has three splits; only 0 and 2 are matched
#         {"date": "2025-08-10", "splits": [
#             {"category": "A", "memo": "a", "amount": Decimal("-1.00")},
#             {"category": "B", "memo": "b", "amount": Decimal("-2.00")},
#             {"category": "C", "memo": "c", "amount": Decimal("-3.00")},
#         ]},
#         # txn 1 has no splits; we match the whole txn key
#         {"date": "2025-08-11", "amount": "-9.99"},
#     ]
#     matched = {
#         QIFItemKey(0, 0), QIFItemKey(0, 2),  # two split matches
#         QIFItemKey(1, None),                 # whole-transaction match
#     }
#     session = _FakeSessionLegacyMode(txns, matched_keys=matched)
#
#     out = mx.build_matched_only_txns(session)
#
#     # txn 0 retained with filtered splits [0,2]; txn 1 retained whole
#     assert len(out) == 2
#     s0 = out[0]["splits"]
#     assert [s["memo"] for s in s0] == ["a", "c"]
#     assert out[1]["amount"] == "-9.99"
