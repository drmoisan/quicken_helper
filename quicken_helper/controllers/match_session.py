# quicken_helper/match_session.py
"""
MatchSession — protocol-only matching between two transaction streams.

Key points:
• No excel_rows anywhere. The Excel side must be represented as transactions.
• Both sides are coerced to the ITransaction protocol at construction via core_util.convert_value.
• Matching uses quicken_helper.matching.txn_compare.compare_txn (amount gate, date proximity, payee sim).
• Provides greedy one-to-one auto-match, manual match/unmatch, and "why not matched?" explanations.
• Keeps state in a simple, deterministic form to support GUI/exports.

Public surface (stable):
    class MatchSession:
        def __init__(self, txns, excel_txns, *, min_score_default: int = 50) -> None
        def auto_match(self, min_score: int | None = None) -> list[tuple[ITransaction, ITransaction]]
        def manual_match(self, bank_index: int, excel_index: int) -> None
        def manual_unmatch(self, bank_index: int | None = None, excel_index: int | None = None) -> None
        def nonmatch_reason(self, bank_index: int, top_n: int = 3) -> str

        # Accessors to support GUI layers:
        @property def bank_txns(self) -> list[ITransaction]
        @property def excel_txns(self) -> list[ITransaction]
        @property def pairs(self) -> list[tuple[ITransaction, ITransaction]]
        @property def unmatched_bank(self) -> list[ITransaction]
        @property def unmatched_excel(self) -> list[ITransaction]

Migration notes:
• If upstream code previously passed excel_groups, adapt them to ITransaction before constructing
  this class (e.g., using an ExcelTransaction adapter). Alternatively, pass the raw objects and rely
  on core_util.convert_value(ITransaction, x) (requires _PROTOCOL_IMPLEMENTATION mapping).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import (
    Any,
    TypeGuard,
    cast,
)

# Protocols / utilities
from quicken_helper.data_model.interfaces import ITransaction
from quicken_helper.utilities.core_util import (
    convert_value as _core_convert_value,
)

from .transaction_compare import MatchScore, compare_txn

log = logging.getLogger(__name__)

# ---------- helpers ----------


def _is_transaction(obj: Any) -> TypeGuard[ITransaction]:
    """Structural check for ITransaction."""
    # Only presence is required for Protocol narrowing; values can be None.
    required_attrs = (
        "account",
        "type",
        "date",
        "action_chk",
        "amount",
        "cleared",
        "payee",
    )
    for name in required_attrs:
        if not hasattr(obj, name):
            return False
    return True


def _coerce_txns(txns: Iterable[object]) -> list[ITransaction]:
    """Ensure all items conform to ITransaction, converting when possible."""

    out: list[ITransaction] = []
    for item in txns:
        txn = _ensure_transaction(item)
        out.append(txn)
    return out


def _ensure_transaction(item: object) -> ITransaction:
    """
    Convert ``item`` to ``ITransaction`` via ``convert_value`` and structural validation.

    Raises ``TypeError`` if the object cannot satisfy the protocol.
    """

    candidate: object | None
    try:
        candidate = convert_value(ITransaction, item)
    except Exception:
        candidate = None

    if candidate is not None and _is_transaction(candidate):
        return candidate

    if _is_transaction(item):
        return item

    raise TypeError(
        f"Expected ITransaction; got {type(item).__name__} lacking required attributes."
    )


def _sort_key_for_match(ms: MatchScore) -> tuple[float, float, float]:
    # 1) Higher score wins → negate
    score_component = -float(ms.score)

    # 2) Smaller date delta wins; None → +inf
    dd_raw = ms.features.get("date_days")
    if dd_raw is None:
        date_component = float("inf")
    elif isinstance(dd_raw, int | float):
        date_component = float(dd_raw)
    elif isinstance(dd_raw, str):
        try:
            date_component = float(int(dd_raw))
        except ValueError:
            date_component = float("inf")
    else:
        date_component = float("inf")

    # 3) Higher payee similarity wins → negate
    ps_raw = ms.features.get("payee_sim", 0.0)
    if isinstance(ps_raw, int | float):
        payee_component = -float(ps_raw)
    elif isinstance(ps_raw, str):
        try:
            payee_component = -float(ps_raw)
        except ValueError:
            payee_component = -0.0
    else:
        payee_component = -0.0

    return (score_component, date_component, payee_component)


# Legacy alias retained for tests/monkeypatching.
convert_value = _core_convert_value


# ---------- core class ----------


class MatchSession:
    """
    Manages matching between two transaction sequences (bank vs excel), both as ITransaction.

    All state is kept in terms of protocol objects and index-based selections suitable for GUI use.
    """

    # --- construction ---

    def __init__(
        self,
        txns: Iterable[object],
        excel_txns: Iterable[object],
        *,
        min_score_default: int = 50,
    ) -> None:
        """
        Initialize the session with two sources of transactions (any runtime type).
        Both sequences will be coerced to the ITransaction protocol using convert_value.

        Args:
            txns: Bank/QIF side transactions or objects convertible to ITransaction.
            excel_txns: Excel side transactions or objects convertible to ITransaction.
            min_score_default: default threshold used by auto_match if not overridden.
        """
        self._bank_txns: list[ITransaction] = _coerce_txns(txns)
        self._excel_txns: list[ITransaction] = _coerce_txns(excel_txns)

        # Greedy assignment state (index pairs). Keep simple for GUI wiring.
        self._pairs_ix: dict[int, int] = {}  # bank_index -> excel_index

        # Cache of last auto-match call (convenience, non-authoritative)
        self._auto_pairs_cache: list[tuple[ITransaction, ITransaction]] = []

        # Default threshold for acceptance
        self._min_score_default: int = int(min_score_default)

    # --- public properties ---

    @property
    def bank_txns(self) -> list[ITransaction]:
        return self._bank_txns

    @property
    def excel_txns(self) -> list[ITransaction]:
        return self._excel_txns

    @property
    def pairs(self) -> list[tuple[ITransaction, ITransaction]]:
        """Return current pairs in bank index order."""
        out: list[tuple[ITransaction, ITransaction]] = []
        for bi, ei in sorted(self._pairs_ix.items()):
            out.append((self._bank_txns[bi], self._excel_txns[ei]))
        return out

    @property
    def unmatched_bank(self) -> list[ITransaction]:
        matched_bank = set(self._pairs_ix.keys())
        return [t for i, t in enumerate(self._bank_txns) if i not in matched_bank]

    @property
    def unmatched_excel(self) -> list[ITransaction]:
        matched_excel = set(self._pairs_ix.values())
        return [t for j, t in enumerate(self._excel_txns) if j not in matched_excel]

    # --- matching ---

    def auto_match(
        self, min_score: int | None = None
    ) -> list[tuple[ITransaction, ITransaction]]:
        """
        Greedy one-to-one matching between bank and excel transactions using compare_txn.

        Amount equality is enforced inside compare_txn (legacy gate). Among equal-amount candidates,
        we pick the highest score, breaking ties by (closest date, highest payee similarity).

        Side effects:
            • Updates self._pairs_ix to reflect the greedy assignment (resets prior pairs).
            • Updates self._auto_pairs_cache to the materialized (txn, txn) pairs.

        Args:
            min_score: Optional threshold to accept a pair. Defaults to self._min_score_default.

        Returns:
            List of accepted (bank_txn, excel_txn) pairs in bank index order.
        """
        threshold: int = (
            self._min_score_default if min_score is None else int(min_score)
        )

        self._pairs_ix.clear()
        self._auto_pairs_cache.clear()

        # Pre-index excel candidates by amount for quick filtering
        by_amount: dict[str, list[int]] = {}  # str(amount) -> list of excel indices
        for j, et in enumerate(self._excel_txns):
            by_amount.setdefault(str(et.amount), []).append(j)

        used_excel: set[int] = set()

        for bi, bt in enumerate(self._bank_txns):
            candidates_ix = [
                j for j in by_amount.get(str(bt.amount), []) if j not in used_excel
            ]
            if not candidates_ix:
                continue

            scored: list[tuple[MatchScore, int]] = []
            for j in candidates_ix:
                ms = compare_txn(bt, self._excel_txns[j])
                scored.append((ms, j))

            # Choose best via deterministic tie-breaking
            scored.sort(key=lambda t: _sort_key_for_match(t[0]))
            best_ms, best_j = scored[0]

            if best_ms.score < threshold:
                continue

            self._pairs_ix[bi] = best_j
            used_excel.add(best_j)

        # Materialize cache
        for bi in sorted(self._pairs_ix.keys()):
            ei = self._pairs_ix[bi]
            self._auto_pairs_cache.append((self._bank_txns[bi], self._excel_txns[ei]))

        return list(self._auto_pairs_cache)

    # --- manual operations ---

    def manual_match(self, bank_index: int, excel_index: int) -> None:
        """
        Manually pair a single bank transaction with a single excel transaction.
        Overrides any existing pairing involving either index to keep one-to-one constraint.
        """
        self._assert_index(bank_index, side="bank")
        self._assert_index(excel_index, side="excel")

        # Unhook any bank -> * pair using this excel index
        for bi, ei in list(self._pairs_ix.items()):
            if ei == excel_index and bi != bank_index:
                del self._pairs_ix[bi]

        # Overwrite any existing pair for this bank index
        self._pairs_ix[bank_index] = excel_index

    def manual_unmatch(
        self, bank_index: int | None = None, excel_index: int | None = None
    ) -> None:
        """
        Remove an existing pairing by bank index OR excel index.

        Args:
            bank_index: bank side index to unpair (if provided)
            excel_index: excel side index to unpair (if provided)

        If both are None, this is a no-op. If both are provided, both are honored.
        """
        if bank_index is not None:
            self._assert_index(bank_index, side="bank")
            self._pairs_ix.pop(bank_index, None)

        if excel_index is not None:
            self._assert_index(excel_index, side="excel")
            for bi, ei in list(self._pairs_ix.items()):
                if ei == excel_index:
                    del self._pairs_ix[bi]

    # --- explanations ---

    def nonmatch_reason(self, bank_index: int, top_n: int = 3) -> str:
        """
        Provide an explanation for why the specified bank transaction is not matched
        (or why a different excel candidate might be preferred).

        Strategy:
            • Score all currently-unmatched excel candidates with compare_txn.
            • If no equal-amount candidates, report that immediately.
            • Otherwise, present the best candidate's reasons and summarize key deltas.

        Returns:
            Human-readable explanation string.
        """
        self._assert_index(bank_index, side="bank")
        bt = self._bank_txns[bank_index]

        matched_excel = set(self._pairs_ix.values())
        candidates: list[tuple[MatchScore, int]] = []
        for j, et in enumerate(self._excel_txns):
            if j in matched_excel:
                continue
            ms = compare_txn(bt, et)
            candidates.append((ms, j))

        # Filter to equal-amount only (compare_txn returns -1000 for amount mismatch)
        equal_amount = [t for t in candidates if t[0].score > -1000]

        if not equal_amount:
            return f"No equal-amount candidates for ${bt.amount}."

        equal_amount.sort(key=lambda t: _sort_key_for_match(t[0]))
        best_ms, best_j = equal_amount[0]

        feat = best_ms.features
        parts: list[str] = []
        parts.append(f"Best candidate index {best_j} (score {best_ms.score}).")
        if feat.get("date_days") is not None:
            parts.append(f"Date Δ = {feat['date_days']} day(s)")
        payee_sim_val = cast("float", feat.get("payee_sim", 0.0))
        parts.append(f"Payee sim = {payee_sim_val:.2f}")
        parts.extend(best_ms.reasons)

        return "; ".join(parts)

    # --- safety ---

    def _assert_index(self, idx: int, *, side: str) -> None:
        if side == "bank":
            if not (0 <= idx < len(self._bank_txns)):
                raise IndexError(f"bank_index out of range: {idx}")
        elif side == "excel":
            if not (0 <= idx < len(self._excel_txns)):
                raise IndexError(f"excel_index out of range: {idx}")
        else:
            raise ValueError(f"Unknown side: {side}")
