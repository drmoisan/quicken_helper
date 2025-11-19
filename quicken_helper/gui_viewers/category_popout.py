# quicken_helper/gui_viewers/category_popout.py
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

try:
    # Keep import local to the module for easy monkeypatching in tests
    from quicken_helper.controllers import match_excel as mex
except Exception:  # pragma: no cover
    mex = None  # will raise at runtime if used without being available

from quicken_helper.controllers.match_session import MatchSession


@dataclass(frozen=True)
class _MB:
    """Minimal interface we expect from a messagebox-like object."""

    showinfo: Callable[[str, str], Any]
    showerror: Callable[[str, str], Any]


def _coerce_txn_dict(txn: Any) -> dict[str, Any]:
    if isinstance(txn, dict):
        typed_txn = cast("dict[Any, Any]", txn)
        converted: dict[str, Any] = {}
        for key_obj, value in typed_txn.items():
            converted[str(key_obj)] = value
        return converted
    as_dict = getattr(txn, "to_dict", None)
    if callable(as_dict):
        result = as_dict()
        if isinstance(result, dict):
            typed_result = cast("dict[Any, Any]", result)
            converted: dict[str, Any] = {}
            for key_obj, value in typed_result.items():
                converted[str(key_obj)] = value
            return converted
    splits_payload: list[dict[str, Any]] = []
    for split in getattr(txn, "splits", []) or []:
        splits_payload.append(
            {
                "category": getattr(split, "category", ""),
                "memo": getattr(split, "memo", ""),
                "amount": getattr(split, "amount", ""),
            }
        )
    return {
        "category": getattr(txn, "category", ""),
        "splits": splits_payload,
    }


def compute_category_sets(
    session: MatchSession, xlsx_path: Path | str
) -> tuple[set[str], set[str]]:
    """
    Compute the set of QIF categories present in the *matched* transactions and the set
    of Excel categories present in the source spreadsheet.

    Relies on controllers.merge_excel helpers:
      - mex.build_matched_only_txns(session)
      - mex.extract_qif_categories(transactions)
      - mex.extract_excel_categories(xlsx_path)
    """
    if mex is None:
        raise RuntimeError("merge_excel module not available")

    matched_txns = mex.build_matched_only_txns(session)
    dict_txns: Sequence[dict[str, Any]] = [
        _coerce_txn_dict(txn) for txn in matched_txns
    ]
    qif_cats: set[str] = set(mex.extract_qif_categories(list(dict_txns)) or set())
    excel_path = Path(xlsx_path)
    excel_cats: set[str] = set(mex.extract_excel_categories(excel_path) or set())
    return qif_cats, excel_cats


def open_normalize_modal(
    master: Any,
    session: MatchSession,
    xlsx_path: Path | str,
    mb: _MB | None = None,
    *,
    show_ui: bool = True,
) -> tuple[set[str], set[str]]:
    """
    Entry point for the 'Normalize Categories' flow.

    Returns:
        (qif_cats, excel_cats) so tests can assert without a GUI.

    Behavior:
      • Computes category sets via compute_category_sets(...)
      • If show_ui=False, only uses mb.showinfo (if provided) and returns.
      • If show_ui=True and a master is provided, you can expand this to build a Toplevel.
        (For now, to keep logic centralized and testable, we simply notify via mb.)
    """
    qif_cats, excel_cats = compute_category_sets(session, xlsx_path)

    if mb is not None:
        mb.showinfo(
            "Normalize Categories",
            (
                "Found categories:\n"
                f"• QIF (matched): {len(qif_cats)}\n"
                f"• Excel: {len(excel_cats)}"
            ),
        )

    # Optionally, you can create a Toplevel UI here if show_ui and master are provided.
    # Left intentionally simple to keep this module unit-test friendly.
    return qif_cats, excel_cats
