# quicken_helper/gui_viewers/helpers.py
from __future__ import annotations

import re
from datetime import date, datetime
from typing import (
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    cast,
    runtime_checkable,
)

# Project module is optional here; we use hasattr-guard in apply_multi_payee_filters
from quicken_helper.legacy import qif_writer as mod

TxnDict = Dict[str, Any]
_DATE_FORMATS = ["%m/%d'%y", "%m/%d/%Y", "%Y-%m-%d"]


# ============================================================================
# Widget Protocols for Helper Functions
# ============================================================================


@runtime_checkable
class TextWidgetProtocol(Protocol):
    """Protocol for Text widget operations used by helper functions."""

    def configure(self, **kwargs: Any) -> Any:
        """Configure widget options."""
        ...

    def delete(self, index1: str, index2: str | None = None) -> None:
        """Delete text from the widget."""
        ...

    def insert(self, index: str, chars: str, *args: Any) -> None:
        """Insert text into the widget."""
        ...


__all__ = [
    "parse_date_maybe",
    "filter_date_range",
    "local_filter_by_payee",
    "apply_multi_payee_filters",
    "set_text",  # Public name
    "fmt_txn",  # Public name
    "fmt_excel_row",  # Public name
    "decode_best_effort",
    "TextWidgetProtocol",
]


def parse_date_maybe(s: str) -> Optional[datetime]:
    s = (s or "").strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    s2 = s.replace("’", "'").replace("`", "'")
    if s2 != s:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(s2, fmt)
            except ValueError:
                continue
    return None


def filter_date_range(
    txns: Sequence[TxnDict], start_str: str, end_str: str
) -> List[TxnDict]:
    def _d(s: str) -> Optional[date]:
        parsed = parse_date_maybe(s)
        return parsed.date() if parsed else None

    start = _d(start_str) if start_str else None
    end = _d(end_str) if end_str else None
    if not start and not end:
        return list(txns)
    out: List[TxnDict] = []
    for t in txns:
        d = parse_date_maybe(str(t.get("date", "")).strip())
        if not d:
            continue
        if start and d.date() < start:
            continue
        if end and d.date() > end:
            continue
        out.append(t)
    return out


def local_filter_by_payee(
    txns: Sequence[TxnDict],
    query: str,
    mode: str = "contains",
    case_sensitive: bool = False,
) -> List[TxnDict]:
    query_cmp = (
        query if (mode in {"regex", "glob"} or case_sensitive) else query.lower()
    )
    out: List[TxnDict] = []
    for t in txns:
        payee_raw = str(t.get("payee", ""))
        payee_cmp = (
            payee_raw
            if (case_sensitive or mode in {"regex", "glob"})
            else payee_raw.lower()
        )
        match = False
        if mode == "contains":
            match = query_cmp in payee_cmp
        elif mode == "exact":
            match = payee_cmp == query_cmp
        elif mode == "startswith":
            match = payee_cmp.startswith(query_cmp)
        elif mode == "endswith":
            match = payee_cmp.endswith(query_cmp)
        elif mode == "glob":
            pattern = (
                "^" + re.escape(query).replace(r"\*", ".*").replace(r"\?", ".") + "$"
            )
            smart_case = case_sensitive or any(
                ch.isalpha() and ch.isupper() for ch in query
            )
            flags = 0 if smart_case else re.IGNORECASE
            match = re.search(pattern, payee_raw, flags) is not None
        elif mode == "regex":
            flags = 0 if case_sensitive else re.IGNORECASE
            match = re.search(query, payee_raw, flags) is not None
        if match:
            out.append(t)
    return out


def apply_multi_payee_filters(
    txns: Sequence[TxnDict],
    queries: Sequence[str],
    mode: str = "contains",
    case_sensitive: bool = False,
    combine: str = "any",
) -> List[TxnDict]:
    queries = [q.strip() for q in queries if q and q.strip()]
    if not queries:
        return list(txns)

    def run_filter(tlist: Sequence[TxnDict], q: str) -> List[TxnDict]:
        tlist_materialized = list(tlist)
        if hasattr(mod, "filter_by_payee"):
            return [
                t
                for t in tlist_materialized
                if t
                in mod.filter_by_payee(
                    tlist_materialized, q, mode=mode, case_sensitive=case_sensitive
                )
            ]
        return local_filter_by_payee(
            tlist_materialized, q, mode=mode, case_sensitive=case_sensitive
        )

    if combine == "any":
        seen: set[int] = set()
        out: List[TxnDict] = []
        for q in queries:
            subset = run_filter(txns, q)
            for t in subset:
                tid = id(t)
                if tid not in seen:
                    seen.add(tid)
                    out.append(t)
        return out
    else:
        cur: List[TxnDict] = list(txns)
        for q in queries:
            cur = run_filter(cur, q)
        return cur


def set_text(widget: TextWidgetProtocol, text: str) -> None:
    """Set text in a Text widget, temporarily enabling it if disabled.

    Args:
        widget: A Text widget supporting configure, delete, and insert operations.
        text: The text content to set in the widget.
    """
    try:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("end", text or "")
        widget.configure(state="disabled")
    except Exception:
        pass


# Backward compatibility alias
_set_text = set_text


def fmt_txn(t: Any) -> str:
    """Format a transaction for display in a Text widget.

    Args:
        t: A transaction object (dict or ITransaction-like) with date, amount, payee, etc.

    Returns:
        A formatted string representation of the transaction.
    """
    if not isinstance(t, Mapping):
        return str(t)
    mapping = cast(Mapping[str, Any], t)

    def g(k: str, d: str = "") -> str:
        return str(mapping.get(k, d) or "")

    lines = [
        f"Date: {g('date')}",
        f"Amount: {g('amount')}",
        f"Payee: {g('payee')}",
        f"Category: {g('category')}",
        f"Memo: {g('memo')}",
        f"Transfer Account: {g('transfer_account')}",
    ]
    splits_raw = mapping.get("splits")
    splits: List[Mapping[str, Any]] = []
    if isinstance(splits_raw, Sequence):
        seq = cast(Sequence[Any], splits_raw)
        for entry in seq:
            entry_obj: Any = entry
            if isinstance(entry_obj, Mapping):
                splits.append(cast(Mapping[str, Any], entry_obj))
            elif hasattr(entry_obj, "to_dict"):
                converted = entry_obj.to_dict()  # type: ignore[attr-defined]
                if isinstance(converted, Mapping):
                    splits.append(cast(Mapping[str, Any], converted))
    if splits:
        lines.append("Splits:")
        for i, s in enumerate(splits, 1):
            lines.append(
                f"  {i}. {str(s.get('category', ''))} | {str(s.get('memo', ''))} | {str(s.get('amount', ''))}"
            )
    return "\n".join(lines)


# Backward compatibility alias
_fmt_txn = fmt_txn


def fmt_excel_row(row: Any) -> str:
    """Format an Excel row for display in a Text widget.

    Args:
        row: An Excel row object (dict or ExcelRow-like) with transaction data.

    Returns:
        A formatted string representation of the Excel row.
    """
    candidate = row.to_dict() if hasattr(row, "to_dict") else row
    if not isinstance(candidate, Mapping):
        return str(candidate)
    mapping = cast(Mapping[str, Any], candidate)

    def g(c: str) -> str:
        return str(mapping.get(c, "") or "")

    cols = [
        "Date",
        "Amount",
        "Item",
        "Canonical MECE Category",
        "Categorization Rationale",
    ]
    return "\n".join(f"{c}: {g(c)}" for c in cols)


# Backward compatibility alias
_fmt_excel_row = fmt_excel_row


# ---------- probe helpers ----------


def _looks_binary(data: bytes) -> bool:
    if not data:
        return False
    sample = data[:4096]
    nul_fraction = sample.count(0) / len(sample)
    if nul_fraction > 0.10:
        return True
    printable = sum(1 for b in sample if 32 <= b <= 126 or b in (9, 10, 13))
    return printable / len(sample) < 0.5


def _too_many_controls(s: str) -> bool:
    if not s:
        return False
    sample = s[:4096]
    controls = sum(1 for ch in sample if ord(ch) < 32 and ch not in ("\n", "\r", "\t"))
    return controls / max(1, len(sample)) > 0.10


def decode_best_effort(data: bytes) -> Optional[str]:
    if _looks_binary(data):
        return None
    for enc in ("utf-8", "utf-16le", "utf-16be", "latin-1"):
        try:
            s = data.decode(enc)
            if _too_many_controls(s):
                continue
            return s
        except Exception:
            continue
    return None
