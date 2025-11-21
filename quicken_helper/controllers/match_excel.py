"""
Excel↔QIF matching helpers.

This module provides utilities to ingest/normalize an Excel categorization sheet,
perform fuzzy category pairing, and drive an end-to-end merge/update of QIF
transactions using Excel as the source of truth.

Primary responsibilities:
• Load Excel rows into ExcelRow records and group them into ExcelTxnGroups.
• Convert Excel groups to protocol-based ITransaction objects for matching.
• Extract and fuzzy-match category names across data sources.
• Build a "matched-only" transaction list from MatchSession results.
• Apply Excel splits to matched bank transactions.
• Emit QIF transactions using protocol-based emitters.
"""

# quicken_helper/controllers/match_excel.py
from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from pathlib import Path

# --- Loading Excel (rows, then grouped by TxnID) ----------------------------
from typing import IO, Any, cast

# We re-use your parser and writer
# from . import qif_to_csv as base
from quicken_helper.controllers.match_helpers import flatten_qif_txns
from quicken_helper.controllers.match_session import MatchSession
from quicken_helper.data_model.excel import map_group_to_excel_txn
from quicken_helper.data_model.excel.excel_row import ExcelRow
from quicken_helper.data_model.excel.excel_txn_group import ExcelTxnGroup
from quicken_helper.data_model.interfaces import ISplit, ITransaction

# from match_session import MatchSession
from quicken_helper.utilities import to_date, to_decimal
from quicken_helper.utilities.excel_io import read_excel_df

log = logging.getLogger(__name__)

__all__ = [
    "build_session_from_paths",
    "load_excel_rows",
    "group_excel_rows",
    "groups_to_excel_transactions",
    "extract_qif_categories",
    "extract_excel_categories",
    "fuzzy_autopairs",
    "_txn_amount",
    "_flatten_qif_txns",
    "build_matched_only_txns",
    "apply_excel_splits",
]

TxnMapping = Mapping[str, object]


def _normalize_split_sequence(raw: object) -> list[Mapping[str, Any]]:
    normalized: list[Mapping[str, Any]] = []
    if isinstance(raw, Sequence) and not isinstance(raw, str | bytes):
        for item in cast("Sequence[object]", raw):
            if isinstance(item, Mapping):
                normalized.append(cast("Mapping[str, Any]", item))
    return normalized


# region Read In Files and Establish Session


def build_session_from_paths(
    bank_txns: list[ITransaction],
    excel_path: Path,
    *,
    min_score_default: int = 50,
) -> MatchSession:
    """
    Master method to read in from source files and build a matching session
    from quicken transactions and an Excel workbook.

    This helper reads `excel_path` into raw Excel rows, groups those rows into
    logical Excel transactions, converts the groups to protocol-compliant
    `ITransaction` objects, and constructs a `MatchSession` with the provided
    `bank_txns` (left side) and the Excel-derived transactions (right side).
    It does **not** call `auto_match()`; the caller may invoke it if desired.

    Args:
        bank_txns: Bank transactions that already satisfy the `ITransaction`
            protocol. These populate the left side of the session unchanged.
        excel_path: Path to the Excel workbook to import. The file is parsed by
            `load_excel_rows()` and grouped by `group_excel_rows()`.
        min_score_default: Default minimum score threshold used by
            `MatchSession` when proposing matches.

    Returns:
        MatchSession: A session containing the provided `bank_txns` and the
        Excel-derived `ITransaction` objects, configured with `min_score_default`.

    Raises:
        FileNotFoundError: If `excel_path` does not exist.
        OSError: If the workbook cannot be opened.
        ValueError: If the workbook contents cannot be parsed into rows or
            grouped into transactions.
        TypeError: If any grouped Excel transaction cannot be mapped to an
            `ITransaction`.

    Notes:
        - This function is type-safe for Pylance: both sides of the session use
          the `ITransaction` protocol, and Excel groups are converted before
          constructing the `MatchSession`.
        - Inputs are not mutated. Any subsequent matching or application of
          updates should be performed by the caller on the returned session.
    """
    rows = load_excel_rows(excel_path)  # existing loader
    groups = group_excel_rows(rows)  # existing grouper
    return make_session(bank_txns, groups, min_score_default=min_score_default)


def load_excel_rows(path: Path) -> list[ExcelRow]:
    """Load and validate an Excel categorization sheet.

    Parameters
    ----------
    path : Path
        File path to the Excel workbook. Expected columns:
        ['TxnID', 'Date', 'Amount', 'Item', 'Canonical MECE Category', 'Categorization Rationale'].

    Returns
    -------
    List[ExcelRow]
        One `ExcelRow` per non-header row with strict types:
        date → datetime.date (via `_parse_date`), amount → Decimal (via `_to_decimal`).

    Raises
    ------
    ValueError
        If any required column is missing.

    Notes
    -----
    - Trims string fields; preserves the original row index for deterministic ordering.
    - Requires pandas (and an Excel engine such as openpyxl).
    """

    df = read_excel_df(path, sheet_name=0)
    needed = [
        "TxnID",
        "Date",
        "Amount",
        "Item",
        "Canonical MECE Category",
        "Categorization Rationale",
    ]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise ValueError(f"Excel is missing columns: {missing}")

    rows: list[ExcelRow] = []
    for pos, (_, r) in enumerate(df.iterrows()):
        d = r["Date"]
        if isinstance(d, datetime):
            dval = d.date()
        elif isinstance(d, date):
            dval = d
        else:
            dval = to_date(str(d))

        rows.append(
            ExcelRow(
                idx=pos,  # 'pos' is an int from enumerate
                txn_id=str(r["TxnID"]).strip(),
                date=dval,
                amount=to_decimal(r["Amount"]),
                memo=str(r["Item"] or "").strip(),
                category=str(r["Canonical MECE Category"] or "").strip(),
                rationale=str(r["Categorization Rationale"] or "").strip(),
            )
        )

    return rows


def group_excel_rows(rows: list[ExcelRow]) -> list[ExcelTxnGroup]:
    """Group `ExcelRow`s by `TxnID` into `ExcelTxnGroup`s.

    The grouping is deterministic: rows within a group keep their original order (by `idx`),
    the group `date` is the earliest row date, and `total_amount` is an exact Decimal sum.

    Parameters
    ----------
    rows : List[ExcelRow]
        Parsed rows from `load_excel_rows`.

    Returns
    -------
    List[ExcelTxnGroup]
        One group per unique `TxnID`, each containing an immutable tuple of member rows.
    """
    by_id: dict[str, list[ExcelRow]] = {}
    for r in rows:
        by_id.setdefault(r.txn_id, []).append(r)
    groups: list[ExcelTxnGroup] = []
    for gid, items in by_id.items():
        items_sorted = sorted(items, key=lambda r: r.idx)
        total = sum((r.amount for r in items_sorted), Decimal("0"))
        first_date = min(r.date for r in items_sorted)
        groups.append(
            ExcelTxnGroup(
                gid=gid,
                date=first_date,
                total_amount=total,
                rows=tuple(items_sorted),
            )
        )
    # Stable order by date then gid
    groups.sort(key=lambda g: (g.date, g.gid))
    return groups


def groups_to_excel_transactions(groups: list[ExcelTxnGroup]) -> list[ITransaction]:
    """
    Adapter to convert grouped Excel rows into protocol transactions suitable for matching.

    This uses the same adapter the GUI uses (map_group_to_excel_txn) so the Excel
    side has the exact ITransaction shape that MatchSession expects.
    """
    return [map_group_to_excel_txn(g) for g in groups]


def make_session(
    bank_txns: list[ITransaction],
    excel_groups: list[ExcelTxnGroup],
    *,
    min_score_default: int = 50,
) -> MatchSession:
    """
    Build a MatchSession from bank-side protocol txns and Excel groups.

    - bank_txns must already satisfy ITransaction (use your QIF loader that returns protocol objects).
    - excel_groups are converted to ITransaction via groups_to_excel_transactions().
    """
    excel_txns: list[ITransaction] = groups_to_excel_transactions(excel_groups)

    # Construct the session with protocol objects on both sides.
    sess = MatchSession(bank_txns, excel_txns, min_score_default=min_score_default)

    # (Optional) Kick off auto-match here, or let the caller/UI decide.
    # sess.auto_match()

    return sess


# endregion Read In Files and Establish Session

# ---------------- Category extraction & matching ----------------


def extract_qif_categories(txns: list[dict[str, Any]]) -> list[str]:
    """Collect unique category names from QIF transactions and their splits.

    Parameters
    ----------
    txns : List[Dict[str, Any]]
        Raw QIF transaction dicts.

    Returns
    -------
    List[str]
        Case-insensitively de-duplicated and sorted category names (first-seen casing retained).
    """
    first_by_lower: dict[str, str] = {}

    def _add(cat: str):
        s = (cat or "").strip()
        if not s:
            return
        key = s.lower()
        # keep first-seen casing for that lowercase key
        if key not in first_by_lower:
            first_by_lower[key] = s

    for t in txns:
        _add(t.get("category", ""))
        empty: Any = []
        for s in t.get("splits") or empty:
            _add(s.get("category", ""))

    # Return values sorted case-insensitively
    return sorted(first_by_lower.values(), key=lambda v: v.lower())


def extract_excel_categories(
    xlsx_path: Path, col_name: str = "Canonical MECE Category"
) -> list[str]:
    """Load Excel and return unique category names from a target column.

    Parameters
    ----------
    xlsx_path : Path
        Path to the Excel workbook.
    col_name : str, optional
        Column to extract from; defaults to "Canonical MECE Category".

    Returns
    -------
    List[str]
        Case-insensitively de-duplicated and sorted category names.

    Raises
    ------
    ValueError
        If the requested column does not exist.
    """
    df = read_excel_df(xlsx_path)
    if col_name not in df.columns:
        raise ValueError(f"Excel missing '{col_name}' column.")

    first_by_lower: dict[str, str] = {}
    for v in df[col_name].dropna().astype(str):
        s = v.strip()
        if not s:
            continue
        key = s.lower()
        if key not in first_by_lower:
            first_by_lower[key] = s

    return sorted(first_by_lower.values(), key=lambda s: s.lower())


def _ratio(a: str, b: str) -> float:
    """Case-insensitive similarity ratio between two strings.

    Returns
    -------
    float
        A value in [0.0, 1.0] from `difflib.SequenceMatcher`.
    """
    return SequenceMatcher(a=a.lower().strip(), b=b.lower().strip()).ratio()


def fuzzy_autopairs(
    qif_cats: list[str],
    excel_cats: list[str],
    threshold: float = 0.84,
) -> tuple[list[tuple[str, str, float]], list[str], list[str]]:
    """
    Greedy one-to-one fuzzy matching:
      - considers all pairs >= threshold similarity
      - picks highest ratio first, then alphabetical tie-breakers
    Returns: (pairs [(data_model, excel, score)], unmatched_qif, unmatched_excel)
    """
    candidates: list[tuple[float, str, str]] = []
    for q in qif_cats:
        for e in excel_cats:
            r = _ratio(q, e)
            if r >= threshold:
                candidates.append((r, q, e))
    candidates.sort(key=lambda x: (-x[0], x[1].lower(), x[2].lower()))

    used_q: set[str] = set()
    used_e: set[str] = set()
    pairs: list[tuple[str, str, float]] = []
    for r, q, e in candidates:
        if q in used_q or e in used_e:
            continue
        pairs.append((q, e, r))
        used_q.add(q)
        used_e.add(e)

    unmatched_q = [q for q in qif_cats if q not in used_q]
    unmatched_e = [e for e in excel_cats if e not in used_e]
    return pairs, unmatched_q, unmatched_e


# --- Matching engine ---------------------------------------------------------


def _txn_amount(txn: TxnMapping) -> Decimal:
    """
    Return the summed split amount if splits exist; otherwise the txn-level amount.
    """

    splits = _normalize_split_sequence(txn.get("splits"))
    if splits:
        total = Decimal("0")
        for split in splits:
            try:
                total += to_decimal(split.get("amount", "0"))
            except Exception:
                continue
        return total

    return to_decimal(txn.get("amount", "0"))


def _flatten_qif_txns(txns: list[dict[str, Any]]) -> list[Any]:
    """
    Compatibility shim exposing the legacy helper from match_helpers.

    .. deprecated::
        This function is maintained for backwards compatibility with existing tests
        and legacy code. It uses deprecated types (QIFTxnView, QIFItemKey) and will
        be removed in a future version. New code should use protocol-based transactions
        and MatchSession directly instead.

    Use MatchSession with protocol-based ITransaction objects for new code.
    """
    return flatten_qif_txns(txns)


def build_matched_only_txns(session: MatchSession) -> list[ITransaction]:
    """
    Return the subset of bank transactions that are matched in the session, in original order.

    The function collects the identity (id) of each bank-side transaction that appears
    in `session.pairs`, then filters `session.bank_txns` by those identities. This
    preserves the original ordering and runs in O(n + p) time where n is the number
    of bank transactions and p is the number of pairs.

    Args:
        session: The current matching session with protocol-based transactions.

    Returns:
        List of bank transactions that have matches, in original order.

    Example:
        >>> session = MatchSession(bank_txns, excel_txns)
        >>> session.auto_match()
        >>> matched = build_matched_only_txns(session)
        >>> # matched contains only bank_txns that appear in session.pairs
    """
    # Build set of bank transaction identities from pairs
    matched_ids = {id(bank_txn) for bank_txn, _ in session.pairs}

    # Filter bank_txns to only matched ones, preserving order
    return [txn for txn in session.bank_txns if id(txn) in matched_ids]


def apply_excel_splits(
    session: MatchSession,
    *,
    clear_top_category: bool = True,
    clone_splits: bool = False,
) -> None:
    """
    Overwrite each matched bank transaction's splits with the splits from its matched
    Excel transaction. Optionally clear the bank txn's top-level category.

    Args:
        session: Current matching session (pairs contain (bank, excel) ITransactions).
        clear_top_category: When True, sets bank.category = "" after assigning splits.
                            This mirrors the legacy behavior when splits exist.
        clone_splits: When True, assigns a new list with copy of split objects
                    (defensive copy). When False, reuses the split objects from
                    the Excel side but assigns a new list.

    Notes:
        - Does not mutate the Excel transactions.
        - Does not change pairing; only the bank side's splits (and optionally category).
    """
    for bank_txn, excel_txn in session.pairs:
        # Get the Excel-side splits; skip if none provided.
        excel_splits: Sequence[ISplit] | None = getattr(excel_txn, "splits", None)  # type: ignore[attr-defined]
        if not excel_splits:
            continue

        # Assign splits on the bank side (new list for safety).
        bank_txn.splits = (
            list(excel_splits) if not clone_splits else [s for s in excel_splits]
        )

        if clear_top_category:
            bank_txn.category = ""


def emit_qif_transactions(txns: Sequence[ITransaction], out: IO[str]) -> None:
    """
    Write the provided transactions to QIF using each transaction's own emitter.

    Supports either:
      • emit_qif(out: IO[str]) -> None
      • to_qif() -> str   (a trailing newline is added if missing)
    """
    for t in txns:
        # Prefer an explicit emitter with the expected signature
        em: object = getattr(
            t, "emit_qif", None
        )  # don't access t.emit_qif directly (keeps typing strict)
        if callable(em):
            cast("Callable[[IO[str]], None]", em)(out)
            continue

        # Fallback: string-producing emitter
        to_qif_fn: object = getattr(t, "to_qif", None)
        if callable(to_qif_fn):
            s = cast("Callable[[], str]", to_qif_fn)()
            out.write(s)
            if not s.endswith("\n"):
                out.write("\n")
            continue

        raise TypeError(
            f"{type(t).__name__} lacks a supported QIF emitter "
            "(expected emit_qif(out) or to_qif())."
        )
