"""Legacy helper utilities kept for backwards compatibility with tests."""

from __future__ import annotations

from datetime import date
from typing import Any

from quicken_helper.legacy.qif_item_key import QIFItemKey
from quicken_helper.legacy.qif_txn_view import QIFTxnView
from quicken_helper.utilities.converters_scalar import to_date, to_decimal

_DATE_FORMATS = ["%m/%d'%y", "%m/%d/%Y", "%Y-%m-%d"]

__all__ = [
    "_flatten_qif_txns",
    "flatten_qif_txns",
    "_candidate_cost",
    "candidate_cost",
]


def _flatten_qif_txns(txns: list[dict[str, Any]]) -> list[QIFTxnView]:
    """Convert loosely typed QIF dicts into deterministic ``QIFTxnView`` rows."""

    out: list[QIFTxnView] = []
    for txn_index, raw in enumerate(txns):
        try:
            txn_date: date = to_date(raw.get("date", ""))
        except Exception:
            # non-transaction record; skip
            continue

        payee = str(raw.get("payee", "") or "")
        memo = str(raw.get("memo", "") or "")
        category = str(raw.get("category", "") or "")

        splits_raw = raw.get("splits")
        if splits_raw:
            for split_index, split in enumerate(splits_raw):
                try:
                    amount = to_decimal(split.get("amount", "0"))
                except Exception:
                    continue
                out.append(
                    QIFTxnView(
                        key=QIFItemKey(txn_index=txn_index, split_index=split_index),
                        date=txn_date,
                        amount=amount,
                        payee=payee,
                        memo=str(split.get("memo", "") or ""),
                        category=str(split.get("category", "") or ""),
                    )
                )
        else:
            try:
                amount = to_decimal(raw.get("amount", "0"))
            except Exception:
                continue
            out.append(
                QIFTxnView(
                    key=QIFItemKey(txn_index=txn_index, split_index=None),
                    date=txn_date,
                    amount=amount,
                    payee=payee,
                    memo=memo,
                    category=category,
                )
            )

    return out


def _candidate_cost(qif_date: date, excel_date: date) -> int | None:
    """Return the absolute day gap when <= 3 days apart; otherwise ``None``."""

    delta = abs((qif_date - excel_date).days)
    return delta if delta <= 3 else None


# Public aliases keep the legacy underscore exports available for tests while
# satisfying pyright's unused-function checks.
flatten_qif_txns = _flatten_qif_txns
candidate_cost = _candidate_cost
