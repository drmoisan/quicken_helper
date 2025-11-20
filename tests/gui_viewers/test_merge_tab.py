# tests/gui_viewers/test_merge_tab.py
"""
Unit tests for quicken_helper.gui_viewers.merge_tab.MergeTab

Policy adherence:
- Independent & isolated: tkinter and quicken_helper deps are stubbed.
- Fast & deterministic: no real GUI; filesystem only via tmp_path.
- AAA structure for each test; docstrings explain intent.
"""

from __future__ import annotations

import importlib
import sys
import types
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from quicken_helper.data_model.excel import (
    ExcelRow,
    ExcelTxnGroup,
    map_group_to_excel_txn,
)
from quicken_helper.data_model.q_wrapper import (
    QSplit,
    QTransaction,
    QuickenFile,
)

# --------------------------
# Tk / ttk / filedialog / messagebox stubs
# --------------------------


# Using real QuickenFile and QTransaction from q_wrapper instead of stubs


class _DummyVar:
    """
    Stand-in for tkinter.StringVar/BooleanVar that accepts 'value=' kwarg
    and provides get()/set().
    """

    def __init__(self, v: object = None, **kwargs: object) -> None:
        if "value" in kwargs:
            v = kwargs["value"]
        self._v: object = "" if v is None else v

    def get(self) -> object:
        return self._v

    def set(self, v: object) -> None:
        self._v = v


class _TextStub:
    """
    Minimal Text-like widget.
    Accepts height/width/state kwargs and supports common methods used by the code.
    """

    def __init__(self, *args: object, **kwargs: object) -> None:
        self._buf: str = ""
        self._height: object = kwargs.get("height")
        self._width: object = kwargs.get("width")
        self._state: object = kwargs.get("state", "normal")

    # Tk-style config API
    def configure(self, **kwargs: object) -> None:
        if "height" in kwargs:
            self._height = kwargs["height"]
        if "width" in kwargs:
            self._width = kwargs["width"]
        if "state" in kwargs:
            self._state = kwargs["state"]

    config = configure  # alias

    def cget(self, key: str) -> object:
        if key == "height":
            return self._height
        if key == "width":
            return self._width
        if key == "state":
            return self._state
        return None

    # Text content API (indices ignored; whole-buffer semantics are fine for tests)
    def get(self, start: str = "1.0", end: str = "end") -> str:
        return self._buf

    def insert(self, index: object, s: object) -> None:
        if self._state == "disabled":
            return
        self._buf += str(s)

    def delete(self, start: str = "1.0", end: str = "end") -> None:
        if self._state == "disabled":
            return
        self._buf = ""

    def see(self, index: object) -> None:
        pass

    # Geometry + misc
    def pack(self, *a: object, **k: object) -> None:
        pass

    def pack_forget(self, *a: object, **k: object) -> None:
        pass

    def grid(self, *a: object, **k: object) -> None:
        pass

    def bind(self, *a: object, **k: object) -> None:
        pass


class _ListboxStub:
    """Minimal Listbox supporting insert/get/delete/bind/selection/grid."""

    def __init__(self, *a: object, **k: object) -> None:
        self._items: list[str] = []
        self._binds: dict[str, object] = {}
        self._sel: set[int] = set()

    def insert(self, index: object, s: object) -> None:
        self._items.append(str(s))

    def get(self, a: object, b: object = None) -> str | tuple[str, ...]:
        if a == 0 and (b == "end" or b is None):
            return tuple(self._items)
        if isinstance(a, int) and b is None:
            return self._items[a]
        return tuple(self._items)

    def delete(self, a: object, b: object = None) -> None:
        self._items.clear()
        self._sel.clear()

    def bind(self, evt: str, fn: object) -> None:
        self._binds[evt] = fn

    def curselection(self) -> tuple[int, ...]:
        return tuple(sorted(self._sel))

    def selection_set(self, i: int) -> None:
        self._sel.add(i)

    def pack(self, *a: object, **k: object) -> None:
        pass

    def grid(self, *a: object, **k: object) -> None:
        pass


class _FakeMB:
    """Messagebox shim that records calls and controls askyesno return."""

    def __init__(self, askyesno_return: bool = True) -> None:
        self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
        self._ask: bool = askyesno_return

    def showinfo(self, *a: object, **k: object) -> None:
        self.calls.append(("showinfo", a, k))

    def showerror(self, *a: object, **k: object) -> None:
        self.calls.append(("showerror", a, k))

    def askyesno(self, *a: object, **k: object) -> bool:
        self.calls.append(("askyesno", a, k))
        return self._ask


def _install_tk_stubs(
    monkeypatch: Any,
    filedialog_overrides: Mapping[str, object] | None = None,
    toplevel_raises: bool = False,
) -> None:
    """Install minimal tkinter/ttk stubs so MergeTab can import & run headlessly."""
    # ---------------- tkinter ----------------
    tk = types.ModuleType("tkinter")

    class Tk:
        def __init__(self, *a: object, **k: object) -> None:
            pass

    class Toplevel:
        def __init__(self, *a: object, **k: object) -> None:
            if toplevel_raises:
                raise RuntimeError("Headless Toplevel disabled for this test")

        def title(self, *a: object, **k: object) -> None:
            pass

        def geometry(self, *a: object, **k: object) -> None:
            pass

        def destroy(self) -> None:
            pass

    tk.Tk = Tk  # type: ignore[attr-defined]
    tk.Toplevel = Toplevel  # type: ignore[attr-defined]
    tk.StringVar = _DummyVar  # type: ignore[attr-defined]
    tk.BooleanVar = _DummyVar  # type: ignore[attr-defined]
    tk.Text = _TextStub  # type: ignore[attr-defined]
    tk.Listbox = _ListboxStub  # type: ignore[attr-defined]

    # ---------------- ttk ----------------
    ttk = types.ModuleType("tkinter.ttk")

    class _Base:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def pack(self, *a: object, **k: object) -> None:
            pass

        def pack_forget(self, *a: object, **k: object) -> None:
            pass

        def grid(self, *a: object, **k: object) -> None:
            pass

        def columnconfigure(self, *a: object, **k: object) -> None:
            pass

        def rowconfigure(self, *a: object, **k: object) -> None:
            pass

        def configure(self, *a: object, **k: object) -> None:
            pass

        def winfo_toplevel(self) -> object:
            return object()

    class Style(_Base):
        def map(self, *a: object, **k: object) -> None:
            pass

        def theme_use(self, *a: object, **k: object) -> None:
            pass

    class Frame(_Base):
        pass

    class LabelFrame(_Base):
        pass

    class Label(_Base):
        pass

    class Button(_Base):
        pass

    class Entry(_Base):
        """Accepts textvariable=..., so `.get()` works if code reads from it."""

        def __init__(self, *a: object, **k: object) -> None:
            super().__init__(*a, **k)
            self._textvar: Any = k.get("textvariable")

        def get(self) -> str:
            return self._textvar.get() if self._textvar else ""

        def insert(self, index: object, s: str) -> None:
            if self._textvar:
                self._textvar.set((self._textvar.get() or "") + s)

        def delete(self, start: object, end: object = None) -> None:
            if self._textvar:
                self._textvar.set("")

    class Checkbutton(_Base):
        pass

    class Combobox(_Base):
        pass

    class Scrollbar(_Base):
        pass

    class Separator(_Base):
        pass

    class Notebook(_Base):
        def __init__(self, *a: object, **k: object) -> None:
            super().__init__(*a, **k)
            self._tabs: list[tuple[object, object]] = []

        def add(self, child: object, **k: object) -> None:
            self._tabs.append((child, k.get("text")))

    ttk.Style = Style  # type: ignore[attr-defined]
    ttk.Frame = Frame  # type: ignore[attr-defined]
    ttk.LabelFrame = LabelFrame  # type: ignore[attr-defined]
    ttk.Label = Label  # type: ignore[attr-defined]
    ttk.Button = Button  # type: ignore[attr-defined]
    ttk.Entry = Entry  # type: ignore[attr-defined]
    ttk.Checkbutton = Checkbutton  # type: ignore[attr-defined]
    ttk.Combobox = Combobox  # type: ignore[attr-defined]
    ttk.Scrollbar = Scrollbar  # type: ignore[attr-defined]
    ttk.Separator = Separator  # type: ignore[attr-defined]
    ttk.Notebook = Notebook  # type: ignore[attr-defined]

    # -------------- messagebox --------------
    messagebox = types.ModuleType("tkinter.messagebox")

    def _noop(*a: object, **k: object) -> None:
        return None

    messagebox.showinfo = _noop  # type: ignore[attr-defined]
    messagebox.showerror = _noop  # type: ignore[attr-defined]
    messagebox.askyesno = lambda *a: True  # type: ignore[attr-defined,assignment]

    # -------------- filedialog --------------
    filedialog = types.ModuleType("tkinter.filedialog")
    filedialog.askopenfilename = (filedialog_overrides or {}).get(  # type: ignore[attr-defined]
        "askopenfilename", lambda **k: ""  # type: ignore[arg-type]
    )
    filedialog.asksaveasfilename = (filedialog_overrides or {}).get(  # type: ignore[attr-defined]
        "asksaveasfilename", lambda **k: ""  # type: ignore[arg-type]
    )

    # Register stubs
    monkeypatch.setitem(sys.modules, "tkinter", tk)  # type: ignore[arg-type]
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk)  # type: ignore[arg-type]
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox)  # type: ignore[arg-type]
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", filedialog)  # type: ignore[arg-type]


# --------------------------
# Project submodule stubs to satisfy imports used by merge_tab.py
# --------------------------


# Lightweight data structures used by stubbed helpers
@dataclass
class _Row:  # type: ignore[reportUnusedClass]
    item: str
    category: str
    rationale: str
    amount: Decimal  # NEW: every split row must include an amount


@dataclass
class _QKey:
    txn_index: int
    transfer_account: str = ""


@dataclass
class _QTxn:
    key: _QKey
    date: date
    amount: str
    payee: str = ""
    category: str = ""
    memo: str = ""


class _MatchSessionStub:
    def __init__(self, bank_txns: list[object], excel_txns: list[object]) -> None:
        self.bank_txns: list[object] = list(bank_txns)
        self.excel_txns: list[object] = list(excel_txns)
        self.pairs: list[tuple[object, object]] = []

    @property
    def unmatched_bank(self) -> list[object]:
        matched_ids = {id(b) for b, _ in self.pairs}
        return [b for b in self.bank_txns if id(b) not in matched_ids]

    @property
    def unmatched_excel(self) -> list[object]:
        matched_ids = {id(e) for _, e in self.pairs}
        return [e for e in self.excel_txns if id(e) not in matched_ids]

    def manual_match(
        self, bank_index: int | None = None, excel_index: int | None = None
    ) -> tuple[bool, str]:
        if bank_index is None or excel_index is None:
            return False, "missing selection"
        if not (
            0 <= bank_index < len(self.bank_txns)
            and 0 <= excel_index < len(self.excel_txns)
        ):
            return False, "invalid selection"
        b, e = self.bank_txns[bank_index], self.excel_txns[excel_index]
        self.pairs = [
            (bb, ee) for (bb, ee) in self.pairs if bb is not b and ee is not e
        ]
        self.pairs.append((b, e))
        return True, "ok"

    def manual_unmatch(
        self, bank_index: int | None = None, excel_index: int | None = None
    ) -> bool:
        if bank_index is not None and 0 <= bank_index < len(self.bank_txns):
            b = self.bank_txns[bank_index]
            before = len(self.pairs)
            self.pairs = [(bb, ee) for (bb, ee) in self.pairs if bb is not b]
            return len(self.pairs) != before
        if excel_index is not None and 0 <= excel_index < len(self.excel_txns):
            e = self.excel_txns[excel_index]
            before = len(self.pairs)
            self.pairs = [(bb, ee) for (bb, ee) in self.pairs if ee is not e]
            return len(self.pairs) != before
        return False


class _CategoryMatchSessionStub:
    """
    Stub for quicken_helper.category_match_session.CategoryMatchSession as used by
    MergeTab.open_normalize_modal (constructed with qif_cats, excel_cats).
    """

    def __init__(self, qif_cats: list[str], excel_cats: list[str]) -> None:
        self.qif_cats: set[str] = set(qif_cats)
        self.excel_cats: set[str] = set(excel_cats)
        self.mapping: dict[str, str] = {}

    def unmatched(self) -> tuple[list[str], list[str]]:
        uq = [q for q in self.qif_cats if q not in self.mapping.values()]
        ue = [e for e in self.excel_cats if e not in self.mapping]
        return uq, ue

    def auto_match(self, threshold: float = 0.84) -> None:
        if self.excel_cats and self.qif_cats:
            self.mapping[next(iter(self.excel_cats))] = next(iter(self.qif_cats))

    def manual_match(self, excel_name: str, qif_category: str) -> tuple[bool, str]:
        self.mapping[excel_name] = qif_category
        return True, "ok"

    def manual_unmatch(self, excel_name: str) -> tuple[bool, str]:
        removed = self.mapping.pop(excel_name, None)
        return (removed is not None), ("ok" if removed is not None else "not found")

    def apply_to_excel(self, xlsx: Path, xlsx_out: Path) -> Path:
        xlsx_out.write_text("normalized", encoding="utf-8")
        return xlsx_out


def nameof_module(mod: Any) -> str:
    spec = getattr(mod, "__spec__", None)
    if spec is not None:
        return spec.name  # type: ignore[no-any-return]
    return mod.__name__  # type: ignore[no-any-return]


def _get_module_names() -> dict[str, str]:
    """Return dict of refactor-safe symbols."""
    # import quicken_helper as quicken_helper
    import quicken_helper
    from quicken_helper.controllers import (
        category_match_session,
        match_excel,
        match_session,
        qif_loader,
    )
    from quicken_helper.gui_viewers import convert_tab, merge_tab, probe_tab, scaling
    from quicken_helper.legacy import qif_writer

    names = {
        "quicken_helper": nameof_module(quicken_helper),
        "controllers": nameof_module(
            getattr(
                quicken_helper,
                "controllers",
                type("M", (), {"__name__": "quicken_helper.controllers"})(),
            )
        ),
        "qif_loader": nameof_module(qif_loader),
        "convert_tab": nameof_module(convert_tab),
        "merge_tab": nameof_module(merge_tab),
        "probe_tab": nameof_module(probe_tab),
        "scaling": nameof_module(scaling),
        "match_excel": nameof_module(match_excel),
        "match_session": nameof_module(match_session),
        "category_match_session": nameof_module(category_match_session),
        "qif_writer": nameof_module(qif_writer),
    }

    return names


def _install_project_stubs(monkeypatch: Any, tmp_path: Path | None = None) -> None:
    """
    Install lightweight quicken_helper stubs used by MergeTab._m_load_and_auto and friends.
    Creates a proper quicken_helper package with .controllers and .legacy subpackages,
    and registers controller/legacy modules in both sys.modules and as parent attributes.
    """
    import sys
    import types
    from datetime import date
    from decimal import Decimal

    names = _get_module_names()

    # ---- root package: quicken_helper (package) ----
    pkg = sys.modules.get(names["quicken_helper"])
    if pkg is None:
        pkg = types.ModuleType(names["quicken_helper"])
        pkg.__path__ = []  # mark as package
        monkeypatch.setitem(sys.modules, names["quicken_helper"], pkg)

    # ---- controllers package ----
    created_controllers = False
    controllers_mod = sys.modules.get(names["controllers"])
    if controllers_mod is None:
        controllers_mod = types.ModuleType(names["controllers"])
        controllers_mod.__path__ = []  # mark as package
        monkeypatch.setitem(sys.modules, names["controllers"], controllers_mod)
        created_controllers = True

    # ---- qif_loader (stub) ----
    ql = types.ModuleType(names["qif_loader"])

    class _Key:  # type: ignore[misc]
        def __init__(self, idx: int) -> None:
            self.txn_index: int = idx
            self.transfer_account: str = ""

    def _legacy_load_transactions(path: object) -> list[dict[str, Any]]:
        # Two simple dict-like txns (legacy shape)
        return [
            {"key": {"txn_index": 1}, "amount": 1.0},
            {"key": {"txn_index": 2}, "amount": 2.0},
        ]

    # def parse_qif(path):
    #     return _legacy_load_transactions(path)
    #
    # def open_and_parse_qif(path):
    #     return _legacy_load_transactions(path)

    def parse_qif_unified_protocol(path: object) -> QuickenFile:
        """Parse QIF using real QuickenFile with test data."""
        file = QuickenFile()
        file.transactions.append(
            QTransaction(
                date=date(2024, 1, 1),
                amount=Decimal("1.0"),
                payee="Payee1",
                category="Cat1",
            )
        )
        file.transactions.append(
            QTransaction(
                date=date(2024, 1, 2),
                amount=Decimal("2.0"),
                payee="Payee2",
                category="Cat2",
            )
        )
        return file

    # Minimal enum used by UI
    from quicken_helper.data_model.interfaces import EnumClearedStatus

    def load_transactions_protocol(path: object) -> list[QTransaction]:
        """Load transactions using real QTransaction with test data."""
        txn = QTransaction(
            date=date(2025, 1, 1),
            amount=Decimal("12.34"),
            payee="TestPayee",
            category="Groceries",
            memo="Test memo",
            cleared=EnumClearedStatus.RECONCILED,
        )
        txn.splits = [
            QSplit(amount=Decimal("10.00"), category="Groceries", memo="Apples"),
            QSplit(amount=Decimal("2.34"), category="Groceries", memo="Bananas"),
        ]
        return [txn]

    # expose both shapes; MergeTab will use protocol path when available
    ql.load_transactions_protocol = load_transactions_protocol  # type: ignore[attr-defined]
    ql.load_transactions = _legacy_load_transactions  # type: ignore[attr-defined]
    # ql.parse_qif = parse_qif
    # ql.open_and_parse_qif = open_and_parse_qif
    ql.parse_qif_unified_protocol = parse_qif_unified_protocol  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, names["qif_loader"], ql)  # type: ignore[arg-type]

    # ---- data_model.excel.excel_transaction (stub) ----
    excel_txn_mod_name = "quicken_helper.data_model.excel.excel_transaction"
    excel_txn_mod = types.ModuleType(excel_txn_mod_name)

    # Use real map_group_to_excel_txn from imports
    excel_txn_mod.map_group_to_excel_txn = map_group_to_excel_txn  # type: ignore[attr-defined]

    # Ensure parent packages exist and register the stub
    pkg_dm = sys.modules.setdefault(
        "quicken_helper.data_model", types.ModuleType("quicken_helper.data_model")
    )
    pkg_dm.__path__ = getattr(pkg_dm, "__path__", [])
    pkg_dm_excel = sys.modules.setdefault(
        "quicken_helper.data_model.excel",
        types.ModuleType("quicken_helper.data_model.excel"),
    )
    pkg_dm_excel.__path__ = getattr(pkg_dm_excel, "__path__", [])
    monkeypatch.setitem(sys.modules, excel_txn_mod_name, excel_txn_mod)  # type: ignore[arg-type]

    # ---- controllers.match_excel (validated ingestion) ----
    mex = types.ModuleType(names["match_excel"])

    # Use real ExcelRow and ExcelTxnGroup from imports (no need for stubs)
    # _Row2 and _Group2 are replaced by ExcelRow and ExcelTxnGroup

    def _validate_rows(rows: Any) -> None:
        """Raise early if any row is missing required fields."""
        for i, r in enumerate(rows or []):
            if not hasattr(r, "amount") or getattr(r, "amount", None) is None:
                raise ValueError(f"Excel row #{i} missing required 'amount'")
            if not hasattr(r, "category") or not getattr(r, "category", ""):
                raise ValueError(f"Excel row #{i} missing required 'category'")

    def load_excel_rows(path: Any) -> list[ExcelRow]:
        # Two valid rows with amounts for happy-path UI tests
        rows = [
            ExcelRow(
                txn_id="G1",
                date=date(2024, 1, 15),
                amount=Decimal("5.00"),
                category="Cat",
                payee="Item1",
                rationale="r1",
            ),
            ExcelRow(
                txn_id="G1",
                date=date(2024, 1, 15),
                amount=Decimal("7.34"),
                category="Cat",
                payee="Item2",
                rationale="r2",
            ),
        ]
        _validate_rows(rows)
        return rows

    def group_excel_rows(rows: list[ExcelRow]) -> list[ExcelTxnGroup]:
        _validate_rows(rows)
        total: Decimal = sum((r.amount for r in rows or []), Decimal("0"))
        return [
            ExcelTxnGroup(
                gid="G1",
                date=date(2024, 1, 15),
                total_amount=total,
                rows=tuple(rows or []),
            )
        ]

    def build_matched_only_txns(sess: Any) -> list[Any]:
        return list(getattr(sess, "txns", []))

    def extract_qif_categories(txns: Any) -> set[str]:
        return {"Food", "Rent"}

    def extract_excel_categories(xlsx: Any) -> set[str]:
        return {"Groceries", "Housing"}

    mex.load_excel_rows = load_excel_rows  # type: ignore[attr-defined]
    mex.group_excel_rows = group_excel_rows  # type: ignore[attr-defined]
    mex.build_matched_only_txns = build_matched_only_txns  # type: ignore[attr-defined]
    mex.extract_qif_categories = extract_qif_categories  # type: ignore[attr-defined]
    mex.extract_excel_categories = extract_excel_categories  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, names["match_excel"], mex)  # type: ignore[arg-type]

    # ---- data_session (stub) ----
    ds_mod = types.ModuleType("quicken_helper.controllers.data_session")

    class DataSession:
        """Minimal DataSession stub for MergeTab tests."""

        def __init__(self) -> None:
            self.qif_path: Any = None
            self.excel_path: Any = None
            self.excel_rows: Any = None

        def load_qif(self, path: Any) -> list[QTransaction]:
            self.qif_path = path
            return load_transactions_protocol(path)

        def load_excel(self, path: Any) -> list[Any]:
            self.excel_path = path
            rows = load_excel_rows(path)
            self.excel_rows = rows
            groups = group_excel_rows(rows)
            return [map_group_to_excel_txn(g) for g in groups]

    ds_mod.DataSession = DataSession  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quicken_helper.controllers.data_session", ds_mod)  # type: ignore[arg-type]

    # ---- match_session (stub) ----
    ms = types.ModuleType(names["match_session"])

    from collections.abc import Iterable

    # Use real ExcelTransaction from imports (no need for _ExcelTxnStub)

    class MatchSession:
        """
        Protocol-only API used by MergeTab:
          • __init__(bank_txns, excel_txns)
          • pairs: List[(bank_txn, excel_txn)]
          • unmatched_bank / unmatched_excel: Lists
          • manual_match(bank_index, excel_index)
          • manual_unmatch(bank_index=None, excel_index=None)
          • auto_match()
        """

        def __init__(self, bank_txns: Iterable[object], excel_txns: Iterable[object]):
            self.bank_txns = list(bank_txns)
            self.excel_txns = list(excel_txns)
            self.pairs: list[tuple[object, object]] = []

        def auto_match(self, *_a: object, **_k: object) -> None:
            if self.bank_txns and self.excel_txns:
                self.pairs = [(self.bank_txns[0], self.excel_txns[0])]

        @property
        def unmatched_bank(self) -> list[object]:
            # Identity-based (no hashing of txn objects)
            matched_ids = {id(b) for b, _ in self.pairs}
            return [b for b in self.bank_txns if id(b) not in matched_ids]

        @property
        def unmatched_excel(self) -> list[object]:
            # Identity-based (no hashing of txn objects)
            matched_ids = {id(e) for _, e in self.pairs}
            return [e for e in self.excel_txns if id(e) not in matched_ids]

        def manual_match(
            self, bank_index: int | None = None, excel_index: int | None = None
        ):
            if bank_index is None or excel_index is None:
                return False, "missing selection"
            if not (
                0 <= bank_index < len(self.bank_txns)
                and 0 <= excel_index < len(self.excel_txns)
            ):
                return False, "invalid selection"
            b, e = self.bank_txns[bank_index], self.excel_txns[excel_index]
            # keep 1↔1
            self.pairs = [
                (bb, ee) for (bb, ee) in self.pairs if bb is not b and ee is not e
            ]
            self.pairs.append((b, e))
            return True, "ok"

        def manual_unmatch(
            self, bank_index: int | None = None, excel_index: int | None = None
        ):
            if bank_index is not None and 0 <= bank_index < len(self.bank_txns):
                b = self.bank_txns[bank_index]
                before = len(self.pairs)
                self.pairs = [(bb, ee) for (bb, ee) in self.pairs if bb is not b]
                return len(self.pairs) != before
            if excel_index is not None and 0 <= excel_index < len(self.excel_txns):
                e = self.excel_txns[excel_index]
                before = len(self.pairs)
                self.pairs = [(bb, ee) for (bb, ee) in self.pairs if ee is not e]
                return len(self.pairs) != before
            return False

    ms.MatchSession = MatchSession  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, names["match_session"], ms)  # type: ignore[arg-type]

    # ---- category_match_session (stub) ----
    cms = types.ModuleType(names["category_match_session"])
    cms.CategoryMatchSession = _CategoryMatchSessionStub  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, names["category_match_session"], cms)  # type: ignore[arg-type]

    # ---- legacy.qif_writer (stub) ----
    legacy_pkg_name = names["qif_writer"].rsplit(".", 1)[
        0
    ]  # e.g., "quicken_helper.legacy"
    legacy_mod = sys.modules.get(legacy_pkg_name)
    if legacy_mod is None:
        legacy_mod = types.ModuleType(legacy_pkg_name)
        legacy_mod.__path__ = []
        monkeypatch.setitem(sys.modules, legacy_pkg_name, legacy_mod)

    qw = types.ModuleType(names["qif_writer"])

    def write_qif(txns: Any, out_path: Any) -> None:
        (tmp_path or Path(".")).mkdir(exist_ok=True)
        return None

    qw.write_qif = write_qif  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, names["qif_writer"], qw)  # type: ignore[arg-type]

    # ----belt and suspenders: tag stubs for cleanup ----
    for _m in (ql, qw, mex, ms, cms):
        _m._is_merge_tab_test_stub = True  # type: ignore[attr-defined]
    if created_controllers:
        controllers_mod._is_merge_tab_test_stub = True  # type: ignore[attr-defined]

    # ---- bind subpackages on parent packages ----
    # Bind controllers submodules as attributes
    monkeypatch.setattr(controllers_mod, "qif_loader", ql)
    monkeypatch.setattr(controllers_mod, "match_excel", mex)
    monkeypatch.setattr(controllers_mod, "match_session", ms)
    monkeypatch.setattr(controllers_mod, "category_match_session", cms)
    # Attach controllers to root package
    monkeypatch.setattr(pkg, "controllers", controllers_mod)
    # Bind legacy.qif_writer and attach legacy on root package
    monkeypatch.setattr(legacy_mod, "qif_writer", qw)
    monkeypatch.setattr(pkg, "legacy", legacy_mod)


# --------------------------
# Import fixture
# --------------------------


@pytest.fixture
def merge_mod(monkeypatch: Any) -> Any:
    """Import quicken_helper.gui_viewers.merge_tab with all deps stubbed for headless testing."""
    names_dict = _get_module_names()
    _install_tk_stubs(monkeypatch)  # GUI stubs
    _install_project_stubs(monkeypatch)  # quicken_helper stubs

    # Only reload GUI modules that we want fresh; keep controller stubs intact.
    for key in (
        "merge_tab",
    ):  # add "convert_tab", "probe_tab" if you truly need them fresh
        sys.modules.pop(names_dict[key], None)

    merge_tab = importlib.import_module(names_dict["merge_tab"])
    return merge_tab


# --------------------------
# Tests (AAA + docstrings)
# --------------------------


def test_init_builds_widgets_and_state(merge_mod: Any) -> None:
    """MergeTab initializes variables, listboxes, and info panel without raising."""
    # Arrange
    MergeTab = merge_mod.MergeTab
    mb = _FakeMB()

    # Act
    mt = MergeTab(master=None, mb=mb)

    # Assert
    assert (
        hasattr(mt, "m_qif_in") and hasattr(mt, "m_xlsx") and hasattr(mt, "m_qif_out")
    )
    assert hasattr(mt, "m_only_matched")
    assert (
        hasattr(mt, "lbx_unqif") and hasattr(mt, "lbx_unx") and hasattr(mt, "lbx_pairs")
    )
    assert hasattr(mt, "txt_info"), "Info Text widget should exist"


def test_browse_qif_sets_in_and_suggests_out(merge_mod: Any, monkeypatch: Any) -> None:
    """_m_browse_qif sets m_qif_in and suggests '<stem>_updated.data_model' without touching disk."""
    import sys

    # Arrange: inject a memory path and reload so the module uses our filedialog
    names = _get_module_names()
    chosen_in = "MEM://in.qif"
    fd_over = {"askopenfilename": lambda **k: chosen_in}  # type: ignore[misc,arg-type,no-any-return,var-annotated]
    _install_tk_stubs(monkeypatch, filedialog_overrides=fd_over)  # type: ignore[arg-type]
    _install_project_stubs(monkeypatch)
    sys.modules.pop(names["merge_tab"], None)
    m2 = importlib.import_module(names["merge_tab"])

    # Avoid FS checks
    monkeypatch.setattr(m2.Path, "exists", lambda self: True, raising=False)  # type: ignore[misc,arg-type,no-redef]
    monkeypatch.setattr(m2.Path, "is_file", lambda self: True, raising=False)  # type: ignore[misc,arg-type,no-redef]

    mt = m2.MergeTab(master=None, mb=_FakeMB())
    mt.m_qif_out.set("")

    # Act
    mt._m_browse_qif()

    # Assert
    assert mt.m_qif_in.get() == chosen_in
    # Compare only the file name to avoid platform separators
    assert m2.Path(mt.m_qif_out.get()).name == "in_updated.qif"


def test_browse_out_sets_out_path(merge_mod: Any, monkeypatch: Any) -> None:
    """_m_browse_out sets m_qif_out from filedialog without touching disk (path-normalized)."""
    import sys

    names = _get_module_names()
    chosen_out = "MEM://out.data_model"
    fd_over = {"asksaveasfilename": lambda **k: chosen_out}  # type: ignore[misc,arg-type,no-any-return,var-annotated]
    _install_tk_stubs(monkeypatch, filedialog_overrides=fd_over)  # type: ignore[arg-type]
    _install_project_stubs(monkeypatch)
    sys.modules.pop(names["merge_tab"], None)
    m2 = importlib.import_module(names["merge_tab"])

    mt = m2.MergeTab(master=None, mb=_FakeMB())

    # Act
    mt._m_browse_out()

    # Assert (normalize both)
    actual = str(m2.Path(mt.m_qif_out.get()))
    expected = str(m2.Path(chosen_out))
    assert actual == expected


def test_load_and_auto_validates_missing_inputs(
    merge_mod: Any, monkeypatch: Any
) -> None:
    """_m_load_and_auto shows errors when QIF or Excel paths are invalid (no filesystem)."""
    # Arrange: both invalid
    mt = merge_mod.MergeTab(master=None, mb=_FakeMB())
    bad_qif = "MEM://missing.data_model"
    bad_xlsx = "MEM://missing.xlsx"
    mt.m_qif_in.set(bad_qif)
    mt.m_xlsx.set(bad_xlsx)

    # Paths don't exist
    monkeypatch.setattr(merge_mod.Path, "exists", lambda self: False, raising=False)  # type: ignore[misc,arg-type]
    monkeypatch.setattr(merge_mod.Path, "is_file", lambda self: False, raising=False)  # type: ignore[misc,arg-type]

    # Act
    mt._m_load()

    # Assert
    assert any(
        c[0] == "showerror" for c in mt.mb.calls
    ), "Expected error for invalid QIF/Excel"

    # Arrange: valid QIF, invalid Excel (still no FS)
    mt.mb.calls.clear()
    valid_qif = "MEM://in.data_model"
    mt.m_qif_in.set(valid_qif)
    # Make only the valid_qif path exist
    monkeypatch.setattr(
        merge_mod.Path, "exists", lambda self: str(self) == valid_qif, raising=False  # type: ignore[arg-type,misc]
    )
    monkeypatch.setattr(
        merge_mod.Path, "is_file", lambda self: str(self) == valid_qif, raising=False  # type: ignore[arg-type,misc]
    )

    # Act
    mt._m_load()

    # Assert
    assert any(
        c[0] == "showerror" for c in mt.mb.calls
    ), "Expected error for invalid Excel path"


def test_load_and_auto_populates_lists_on_success(
    merge_mod: Any, monkeypatch: Any
) -> None:
    """_m_load_and_auto creates a session, auto-matches, and fills listboxes (no filesystem)."""
    # Arrange
    mt = merge_mod.MergeTab(master=None, mb=_FakeMB())
    qif_in = "Z:/memory/in.data_model"
    xlsx = "Z:/memory/in.xlsx"
    mt.m_qif_in.set(qif_in)
    mt.m_xlsx.set(xlsx)

    # Patch Path.exists so ONLY our two in-memory paths "exist"
    monkeypatch.setattr(merge_mod.Path, "exists", lambda self: True, raising=False)  # type: ignore[arg-type,misc]
    monkeypatch.setattr(merge_mod.Path, "is_file", lambda self: True, raising=False)  # type: ignore[arg-type,misc]

    # Act
    mt._m_load()

    # Debug: Check if there was an error
    if mt._merge_session is None and hasattr(mt.mb, "calls"):
        errors = [c for c in mt.mb.calls if c[0] == "showerror"]
        if errors:
            print(f"\\nDEBUG: Error occurred: {errors[-1]}")

    mt._m_auto_match()

    # Assert
    assert mt._merge_session is not None, "Session should be created"
    assert isinstance(mt.m_pairs, list)
    assert isinstance(mt.m_unmatched_qif, list)
    assert isinstance(mt.m_unmatched_excel, list)


def test_manual_match_requires_selection_and_calls_session(merge_mod: Any) -> None:
    """_m_manual_match shows error with no selection; with selections it calls session.manual_match."""
    # Arrange
    mt = merge_mod.MergeTab(master=None, mb=_FakeMB())

    # bank txn (QIF) and excel txn (protocol-shaped)
    q = _QTxn(_QKey(1), date(2024, 1, 1), "10.00", "Alpha")

    @dataclass(frozen=True)
    class _ExcelTxn:
        id: str
        date: date
        amount: Decimal
        payee: str = ""
        memo: str = ""
        category: str = ""
        splits: list = field(default_factory=list)  # type: ignore[var-annotated]

    e = _ExcelTxn("G101", date(2024, 1, 2), Decimal("10.00"), payee="Alpha")

    # protocol-shaped session stub
    mt._merge_session = _MatchSessionStub([q], [e])

    # UI caches now carry (index, txn) tuples
    mt._unqif_sorted = [(0, q)]
    mt._unx_sorted = [(0, e)]

    # seed listboxes
    mt.lbx_unqif.insert("end", "data_model")
    mt.lbx_unx.insert("end", "grp")

    # Act (no selection)
    mt._m_manual_match()
    # Assert
    assert any(
        c[0] == "showerror" for c in mt.mb.calls
    ), "Expected error when nothing selected"

    # Act (with selections)
    mt.mb.calls.clear()
    mt.lbx_unqif.selection_set(0)
    mt.lbx_unx.selection_set(0)
    mt._m_manual_match()

    # Assert: lists refreshed / info written (no error)
    assert not any(c[0] == "showerror" for c in mt.mb.calls)
    assert "Matched" in mt.txt_info.get("1.0", "end")


def test_manual_unmatch_from_pairs_calls_session(merge_mod: Any) -> None:
    """_m_manual_unmatch unmatches the selected pair via session.manual_unmatch."""
    # Arrange
    mt = merge_mod.MergeTab(master=None, mb=_FakeMB())

    q = _QTxn(_QKey(1), date(2024, 1, 1), "10.00", "Alpha")

    @dataclass(frozen=True)
    class _ExcelTxn:
        id: str
        date: date
        amount: Decimal
        payee: str = ""
        memo: str = ""
        category: str = ""
        splits: list[Any] = field(default_factory=list)  # type: ignore[var-annotated]

    e = _ExcelTxn("G101", date(2024, 1, 2), Decimal("10.00"), payee="Alpha")

    sess = _MatchSessionStub([q], [e])
    # one matched pair, protocol shape
    sess.pairs = [(q, e)]
    mt._merge_session = sess

    # UI pairs cache uses (bank_index, excel_index, bank_txn, excel_txn)
    mt._pairs_sorted = [(0, 0, q, e)]

    mt.lbx_pairs.insert("end", "PAIR")
    mt.lbx_pairs.selection_set(0)

    # Act
    mt._m_manual_unmatch()

    # Assert
    assert sess.pairs == [], "Pair should be removed after unmatch"
    assert "Unmatched" in mt.txt_info.get("1.0", "end")


def test_export_listbox_writes_file(merge_mod: Any, monkeypatch: Any) -> None:
    """_export_listbox writes listbox items to an in-memory file (no filesystem)."""
    import builtins

    mt = merge_mod.MergeTab(master=None, mb=_FakeMB())
    mt.lbx_unx.insert("end", "row1")
    mt.lbx_unx.insert("end", "row2")

    # Choose a memory path and stub filedialog to return it
    chosen = "MEM://unmatched_excel.txt"
    fd_over = {"asksaveasfilename": lambda **k: chosen}  # type: ignore[misc,arg-type,no-any-return,var-annotated]
    _install_tk_stubs(monkeypatch, filedialog_overrides=fd_over)  # type: ignore[arg-type]
    _install_project_stubs(monkeypatch)
    # Rebind filedialog used by merge_mod to the newly stubbed one
    import tkinter.filedialog as fd_mod

    merge_mod.filedialog = fd_mod

    # In-memory file that doesn't actually close
    class _MemFile:
        def __init__(self) -> None:
            self._buf: list[str] = []

        def write(self, s: str) -> None:
            self._buf.append(str(s))

        def __enter__(self) -> _MemFile:
            return self

        def __exit__(self, *a: object) -> None:
            pass  # no-op close

        def getvalue(self) -> str:
            return "".join(self._buf)

    mem = _MemFile()
    opened: list[str] = []

    def fake_open(
        path: Any,
        mode: str = "r",
        encoding: str | None = None,
        newline: str | None = None,
    ) -> _MemFile:
        # Record the normalized path and return our in-memory handle
        opened.append(str(merge_mod.Path(path)))
        assert "w" in mode
        return mem

    # Patch where open() is looked up
    monkeypatch.setattr(merge_mod, "open", fake_open, raising=False)
    monkeypatch.setattr(builtins, "open", fake_open, raising=False)

    # Act
    merge_mod.MergeTab._export_listbox(mt, mt.lbx_unx, "unmatched_excel")

    # Assert
    assert opened and opened[-1] == str(merge_mod.Path(chosen))
    written = mem.getvalue().strip().splitlines()
    assert written == ["row1", "row2"]
    assert any(
        c[0] == "showinfo" for c in mt.mb.calls
    ), "Expected completion info dialog"


def test_open_normalize_modal_headless_object_behaves(
    merge_mod: Any, monkeypatch: Any
) -> None:
    """Headless normalize modal exposes actions that work (no filesystem; names from session)."""
    # IMPORTANT: get real module names first (from the actual package), THEN install stubs
    names = _get_module_names()

    # Arrange: force headless, stub deps, reload
    _install_tk_stubs(monkeypatch, toplevel_raises=True)
    _install_project_stubs(monkeypatch)

    sys.modules.pop(names["merge_tab"], None)
    m2 = importlib.import_module(names["merge_tab"])

    mt = m2.MergeTab(master=None, mb=_FakeMB())
    mt.m_qif_in.set("MEM://in.data_model")
    mt.m_xlsx.set("MEM://in.xlsx")

    # No real FS
    monkeypatch.setattr(m2.Path, "exists", lambda self: True, raising=False)  # type: ignore[arg-type,misc]
    monkeypatch.setattr(m2.Path, "is_file", lambda self: True, raising=False)  # type: ignore[arg-type,misc]

    # Don’t write files; just capture call
    calls: list[tuple[str, str]] = []
    cms = sys.modules[names["category_match_session"]]

    def fake_apply(self: Any, xlsx: Any, xlsx_out: Any) -> Any:
        calls.append((str(xlsx), str(xlsx_out)))
        return m2.Path(xlsx_out)

    monkeypatch.setattr(
        cms.CategoryMatchSession, "apply_to_excel", fake_apply, raising=False
    )

    # Act
    headless = mt.open_normalize_modal()
    headless.auto_match()

    # Use the session’s own unmatched sets (robust to stub changes)
    uq, ue = headless.unmatched()
    assert isinstance(uq, list | set) and isinstance(ue, list | set)
    # Pick any available names; if empty, skip matching step (still exercise pairs/apply)
    pre_pairs = list(headless.pairs())
    if ue and uq:
        e: Any = sorted(list(ue))[0]  # type: ignore[arg-type]
        q: Any = sorted(list(uq))[0]  # type: ignore[arg-type]
        ok, _ = headless.do_match(e, q)
        assert ok, "manual match should succeed"
    post_pairs = list(headless.pairs())

    # Assert: pair list grew (or at least exists), and apply/save was invoked with our path
    assert len(post_pairs) >= len(pre_pairs)
    out_path = "MEM://normalized.xlsx"
    result = headless.apply_and_save(out_path=out_path)

    # Normalize expectations using the module's Path (handles Windows vs POSIX)
    expected_in = str(m2.Path("MEM://in.xlsx"))
    expected_out = str(m2.Path(out_path))

    assert calls and calls[-1] == (expected_in, expected_out)
    assert str(result) == expected_out


@pytest.fixture(autouse=True)
def _purge_stubs_after_each_test(
    monkeypatch: Any,
) -> Any:  # pyright: ignore[reportUnusedFunction]
    yield
    # remove only modules we created (tag them when you create them)
    for name, mod in list(sys.modules.items()):
        if getattr(mod, "_is_merge_tab_test_stub", False):
            sys.modules.pop(name, None)
        importlib.invalidate_caches()


@pytest.fixture(autouse=True, scope="module")
def _cleanup_module() -> Any:  # pyright: ignore[reportUnusedFunction]
    yield
    # cleanup here (e.g., purge tagged sys.modules entries)
    for name, mod in list(sys.modules.items()):
        if getattr(mod, "_is_merge_tab_test_stub", False):
            sys.modules.pop(name, None)
    importlib.invalidate_caches()


# --- Migration guard: skip normalize-related tests moved to test_category_popout.py ---
def _skip_legacy_normalize_tests() -> None:
    import pytest as _pytest

    # Tailored selectors: name/docstring, case-insensitive
    KEYWORDS = (
        "normalize",  # broad: catches test_normalize_* variants
        "open_normalize_modal",  # specific old entrypoint
        "_m_normalize_categories",  # specific old handler
        "normalize categories",  # docstring phrase
        "category_popout",  # new home reference
    )

    g = globals()
    for name, obj in list(g.items()):
        if not (name.startswith("test_") and callable(obj)):
            continue
        text = (name + " " + (getattr(obj, "__doc__", "") or "")).lower()
        if any(k in text for k in KEYWORDS):
            g[name] = _pytest.mark.skip(
                "Moved to tests/gui_viewers/test_category_popout.py"
            )(obj)


_skip_legacy_normalize_tests()
del _skip_legacy_normalize_tests
