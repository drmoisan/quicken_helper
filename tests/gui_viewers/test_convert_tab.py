# tests/gui_viewers/test_convert_tab.py
"""
Unit tests for quicken_helper.gui_viewers.convert_tab.ConvertTab

Policy compliance:
- Independence & Isolation: Tk/Ttk, dialogs, filesystem, and external controllers are stubbed/mocked.
- Fast & Deterministic: No external I/O or randomness; all outcomes repeatable.
- Readability: AAA structure; each test includes a docstring describing intent.
- Scenarios: Positive/negative paths for conversion, extension logic, overwrite prompt, parsing & filtering hooks.

These tests DO NOT touch the real filesystem.
"""

from __future__ import annotations

import importlib
import sys
import types
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

# --------------------------
# Minimal tkinter stubs (headless)
# --------------------------


def _install_tk_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install minimal tkinter/ttk/font/messagebox/filedialog stubs usable by ConvertTab."""

    # --- tkinter base module ---
    tk = types.ModuleType("tkinter")

    class _VarBase:
        def __init__(self, value: Any = None) -> None:
            self._v: Any = value

        def get(self) -> Any:
            return self._v

        def set(self, v: Any) -> None:
            self._v = v

        def trace_add(self, *a: object, **k: object) -> str:
            return "token"  # used by emit_var

    class Tk:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def withdraw(self) -> None:
            pass

        def mainloop(self) -> None:
            pass

        def after(
            self, ms: int, func: Callable[..., object] | None = None, *args: object
        ) -> None:  # execute immediately in tests
            if func is not None:
                func(*args)

    class StringVar(_VarBase):
        def __init__(self, value: str = "") -> None:
            super().__init__(value)

    class BooleanVar(_VarBase):
        def __init__(self, value: bool = False) -> None:
            super().__init__(value)

    class IntVar(_VarBase):
        def __init__(self, value: int = 0) -> None:
            super().__init__(value)

    class Text:
        def __init__(self, *a: object, **k: object) -> None:
            self.master: object = a[0] if a else None
            self._buf: str = ""

        def get(self, s: object, e: object) -> str:
            return self._buf

        def insert(self, i: object, s: str) -> None:
            self._buf += s

        def delete(self, s: object, e: object) -> None:
            self._buf = ""

        def see(self, i: object) -> None:
            pass

        # geometry & events
        def grid(self, *a: object, **k: object) -> None:
            pass

        def pack(self, *a: object, **k: object) -> None:
            pass

        def grid_remove(self, *a: object, **k: object) -> None:
            pass

        def bind(self, *a: object, **k: object) -> None:
            pass

    # Export tkinter symbols
    tk.Tk = Tk  # type: ignore[attr-defined]
    tk.StringVar = StringVar  # type: ignore[attr-defined]
    tk.BooleanVar = BooleanVar  # type: ignore[attr-defined]
    tk.IntVar = IntVar  # type: ignore[attr-defined]
    tk.Text = Text  # type: ignore[attr-defined]
    tk.END = "end"  # type: ignore[attr-defined]
    tk.INSERT = "insert"  # type: ignore[attr-defined]

    # --- tkinter.ttk submodule ---
    ttk = types.ModuleType("tkinter.ttk")

    class _Widget:
        def __init__(self, *a: object, **k: object) -> None:
            # emulate Tkinter storing parent on every widget
            self.master: object = a[0] if a else None

        def pack(self, *a: object, **k: object) -> None:
            pass

        def grid(self, *a: object, **k: object) -> None:
            pass

        def place(self, *a: object, **k: object) -> None:
            pass

        def grid_remove(self, *a: object, **k: object) -> None:
            pass

        def columnconfigure(self, *a: object, **k: object) -> None:
            pass

        def rowconfigure(self, *a: object, **k: object) -> None:
            pass

        def bind(self, *a: object, **k: object) -> None:
            pass

        def configure(self, *a: object, **k: object) -> None:
            pass

        def destroy(self, *a: object, **k: object) -> None:
            pass

        def winfo_ismapped(self) -> bool:
            return True

        def update_idletasks(self) -> None:
            pass  # used in ConvertTab.logln()

    class Frame(_Widget):
        pass

    class LabelFrame(Frame):
        pass

    class Label(_Widget):
        pass

    class Button(_Widget):
        pass

    class Entry(_Widget):
        pass

    class Checkbutton(_Widget):
        pass

    class Radiobutton(_Widget):
        pass

    class Combobox(_Widget):
        def __init__(
            self,
            *a: object,
            values: list[str] | None = None,
            textvariable: Any = None,
            **k: object,
        ) -> None:
            super().__init__(*a, **k)
            self._values: list[str] = values or []
            self._tv: Any = textvariable

        def set(self, v: str) -> None:
            if self._tv:
                self._tv.set(v)

        def get(self) -> str:
            return (
                self._tv.get()
                if self._tv
                else (self._values[0] if self._values else "")
            )

        def current(self, idx: int) -> None:
            if self._values and 0 <= idx < len(self._values):
                self.set(self._values[idx])

    class Notebook(Frame):
        def add(self, *a: object, **k: object) -> None:
            pass

    class Style:
        def theme_use(self, *a: object, **k: object) -> None:
            pass

        def configure(self, *a: object, **k: object) -> None:
            pass

        def map(self, *a: object, **k: object) -> None:
            pass

    class Separator(_Widget):
        pass

    class Progressbar(_Widget):
        pass

    ttk.Frame = Frame  # type: ignore[attr-defined]
    ttk.LabelFrame = LabelFrame  # type: ignore[attr-defined]
    ttk.Label = Label  # type: ignore[attr-defined]
    ttk.Button = Button  # type: ignore[attr-defined]
    ttk.Entry = Entry  # type: ignore[attr-defined]
    ttk.Checkbutton = Checkbutton  # type: ignore[attr-defined]
    ttk.Radiobutton = Radiobutton  # type: ignore[attr-defined]
    ttk.Combobox = Combobox  # type: ignore[attr-defined]
    ttk.Notebook = Notebook  # type: ignore[attr-defined]
    ttk.Style = Style  # type: ignore[attr-defined]
    ttk.Separator = Separator  # type: ignore[attr-defined]
    ttk.Progressbar = Progressbar  # type: ignore[attr-defined]

    # --- filedialog and messagebox ---
    filedialog = types.ModuleType("tkinter.filedialog")
    filedialog.askopenfilename = lambda **k: ""  # type: ignore[attr-defined,misc]
    filedialog.asksaveasfilename = lambda **k: ""  # type: ignore[attr-defined,misc]

    messagebox = types.ModuleType("tkinter.messagebox")

    class _FakeMB:
        """Captures info/error prompts and simulates overwrite confirmations."""

        def __init__(self, ask: bool = True) -> None:
            self.calls: list[tuple[str, tuple[object, ...], dict[str, object]]] = []
            self._ask = ask

        def showinfo(self, *a: object, **k: object) -> None:
            self.calls.append(("showinfo", a, k))

        def showerror(self, *a: object, **k: object) -> None:
            self.calls.append(("showerror", a, k))

        def askyesno(self, *a: object, **k: object) -> bool:
            self.calls.append(("askyesno", a, k))
            return self._ask

    messagebox._FakeMB = _FakeMB  # type: ignore[attr-defined]

    # --- font ---
    font = types.ModuleType("tkinter.font")

    class _Font:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def cget(self, k: str) -> int:
            return 10

        def configure(self, **k: object) -> None:
            pass

    def nametofont(name: str) -> _Font:
        return _Font()

    font.Font = _Font  # type: ignore[attr-defined]
    font.nametofont = nametofont  # type: ignore[attr-defined]

    # Register stubs
    monkeypatch.setitem(sys.modules, "tkinter", tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", filedialog)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox)
    monkeypatch.setitem(sys.modules, "tkinter.font", font)


# --------------------------
# Fixture: import ConvertTab with tkinter stubbed
# --------------------------


@pytest.fixture
def convert_mod(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import convert_tab with Tk/Ttk and dialogs stubbed, ensuring a clean module."""
    _install_tk_stubs(monkeypatch)
    # Ensure a fresh import (avoid prior state)
    sys.modules.pop("quicken_helper.gui_viewers.convert_tab", None)
    return importlib.import_module("quicken_helper.gui_viewers.convert_tab")


def _make_tab(convert_mod: types.ModuleType) -> tuple[Any, Any]:
    """Create a ConvertTab with a proper parent chain and a fake messagebox API."""
    tk = sys.modules["tkinter"]
    root = tk.Tk()  # type: ignore[attr-defined]
    master = convert_mod.ttk.Frame(root)  # parented frame so .master exists
    mb_mod = sys.modules["tkinter.messagebox"]
    mb = mb_mod._FakeMB(ask=True)  # type: ignore[attr-defined]
    tab = convert_mod.ConvertTab(master, mb, session=None)
    return tab, mb


# --------------------------
# Helpers: no-FS parser/writer & Path.exists
# --------------------------


def _patch_qif_parser(
    monkeypatch: pytest.MonkeyPatch, convert_mod: types.ModuleType, n_txns: int = 2
) -> None:
    """Return a fake ledger with transactions regardless of which parser symbol is used."""

    class _Txn:
        def __init__(self, i: int) -> None:
            self.i = i

        def to_dict(self) -> dict[str, object]:
            return {"id": self.i, "amount": "1.00"}

    class _Ledger:
        def __init__(self, n: int) -> None:
            self.transactions = [_Txn(i) for i in range(n)]

    # Patch both potential locations
    monkeypatch.setattr(
        convert_mod,
        "parse_qif_unified_protocol",
        lambda p: _Ledger(n_txns),  # type: ignore[misc]
        raising=False,
    )
    try:
        loader = importlib.import_module("quicken_helper.controllers.qif_loader")
        monkeypatch.setattr(
            loader,
            "parse_qif_unified_protocol",
            lambda p: _Ledger(n_txns),  # type: ignore[misc]
            raising=False,
        )
    except Exception:
        pass


def _patch_csv_writers(
    monkeypatch: pytest.MonkeyPatch,
    convert_mod: types.ModuleType,
    calls: list[tuple[str, int, str]],
) -> None:
    """Record CSV writer invocations without writing files."""

    def _csv_recorder(txns: object, out_path: object) -> None:
        count = len(getattr(txns, "transactions", txns))  # type: ignore[arg-type]
        calls.append(("writer_called", count, str(out_path)))

    # Patch the CSV profile writers in io_service (since io_service imports them at module level)
    try:
        from quicken_helper.controllers import io_service

        monkeypatch.setattr(
            io_service, "write_csv_quicken_windows", _csv_recorder, raising=False
        )
        monkeypatch.setattr(
            io_service, "write_csv_quicken_mac", _csv_recorder, raising=False
        )
    except Exception:
        pass

    # Also patch legacy qif_writer functions used for default CSV modes and QIF writes
    try:
        from quicken_helper.legacy import qif_writer as mod

        monkeypatch.setattr(mod, "write_csv_exploded", _csv_recorder, raising=False)
        monkeypatch.setattr(mod, "write_csv_flat", _csv_recorder, raising=False)
        monkeypatch.setattr(
            mod,
            "write_qif",
            lambda path, txns, **kwargs: calls.append(
                ("writer_called", len(list(txns)), str(path))
            ),
            raising=False,
        )
    except Exception:
        pass


def _patch_helpers_passthrough(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure filter helpers don't alter data (deterministic pass-through)."""
    try:
        helpers = importlib.import_module("quicken_helper.gui_viewers.helpers")
        monkeypatch.setattr(
            helpers,
            "filter_date_range",
            lambda txns, df, dt: txns,  # type: ignore[misc]
            raising=False,
        )
        monkeypatch.setattr(
            helpers,
            "apply_multi_payee_filters",
            lambda txns, *a, **k: txns,  # type: ignore[misc]
            raising=False,
        )
    except Exception:
        pass


def _patch_path_exists(
    monkeypatch: pytest.MonkeyPatch,
    convert_mod: types.ModuleType,
    predicate: Callable[[str], bool],
) -> None:
    """Make Path.exists return predicate(path_str) everywhere (module-local and global Path)."""
    if hasattr(convert_mod, "Path"):
        monkeypatch.setattr(
            convert_mod.Path,
            "exists",
            lambda self: predicate(str(self)),  # type: ignore[misc]
            raising=False,
        )
    monkeypatch.setattr(
        Path, "exists", lambda self: predicate(str(self)), raising=False  # type: ignore[misc]
    )


# --------------------------
# Tests
# --------------------------


def test_update_output_extension_blank_out_uses_in_path(
    convert_mod: types.ModuleType,
) -> None:
    """Arrange: blank out_path, valid .qif in_path; Act: _update_output_extension; Assert: out uses stem + .csv."""
    # Arrange
    tab, _ = _make_tab(convert_mod)
    tab.in_path.set(r"C:\fake\input.qif")
    tab.out_path.set("")
    tab.emit_var.set("csv")
    # Act
    tab._update_output_extension()
    # Assert
    out_str = tab.out_path.get()
    assert out_str.endswith(".csv"), f"Output path should end with .csv: {out_str}"
    assert "input" in out_str, f"Output path should contain 'input': {out_str}"


def test_update_output_extension_switches_extension(
    convert_mod: types.ModuleType,
) -> None:
    """Arrange: out_path with .qif; Act: update for csv emit; Assert: suffix becomes .csv."""
    # Arrange
    tab, _ = _make_tab(convert_mod)
    tab.out_path.set(r"C:\fake\out.qif")
    tab.emit_var.set("csv")
    # Act
    tab._update_output_extension()
    # Assert
    assert Path(tab.out_path.get()).suffix == ".csv"


def test_parse_payee_filters_parses_lines_and_commas(
    convert_mod: types.ModuleType,
) -> None:
    """Arrange: mixed commas/newlines + whitespace; Act: _parse_payee_filters; Assert: trimmed non-empty tokens."""
    # Arrange
    tab, _ = _make_tab(convert_mod)
    tab.payees_text.insert("end", " Alpha,  \nBeta\n\n  ,Gamma ,  ")
    # Act
    got = tab._parse_payee_filters()
    # Assert
    assert got == ["Alpha", "Beta", "Gamma"]


def test_run_missing_input_shows_error(convert_mod: types.ModuleType) -> None:
    """Arrange: missing input; Act: run_conversion; Assert: error dialog reported; no writer call needed."""
    # Arrange
    tab, mb = _make_tab(convert_mod)
    tab.in_path.set("")  # missing
    tab.out_path.set(r"C:\fake\out.csv")
    tab.emit_var.set("csv")
    tab.csv_profile.set("quicken-windows")
    # Act
    tab.run_conversion()
    # Assert
    assert any(
        kind == "showerror" for kind, *_ in mb.calls  # type: ignore[misc]
    ), "Expected error dialog for missing input"


def test_run_missing_output_shows_error(
    convert_mod: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arrange: valid input exists but output missing; Act: run_conversion; Assert: error dialog reported."""
    # Arrange
    tab, mb = _make_tab(convert_mod)
    tab.in_path.set(r"C:\fake\input.qif")
    tab.out_path.set("")  # missing
    tab.emit_var.set("csv")
    tab.csv_profile.set("quicken-windows")
    _patch_path_exists(
        monkeypatch, convert_mod, predicate=lambda p: p.endswith("input.qif")
    )
    # Act
    tab.run_conversion()
    # Assert
    assert any(
        kind == "showerror" for kind, *_ in mb.calls  # type: ignore[misc]
    ), "Expected error dialog for missing output"


def test_run_decline_overwrite_does_not_write(
    convert_mod: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arrange: output 'exists' and user declines; Act: run_conversion; Assert: writer not invoked, confirmation asked."""
    # Arrange
    tab, mb = _make_tab(convert_mod)
    mb._ask = False  # decline overwrite
    tab.in_path.set(r"C:\fake\input.qif")
    tab.out_path.set(r"C:\fake\out.csv")
    tab.emit_var.set("csv")
    tab.csv_profile.set("quicken-windows")
    # both input and output appear to exist
    _patch_path_exists(
        monkeypatch,
        convert_mod,
        predicate=lambda p: p.endswith("input.qif") or p.endswith("out.csv"),
    )
    calls: list[tuple[str, int, str]] = []
    _patch_qif_parser(monkeypatch, convert_mod)
    _patch_csv_writers(monkeypatch, convert_mod, calls)
    # Act
    tab.run_conversion()
    # Assert
    assert not any(
        c[0] == "writer_called" for c in calls
    ), "Writer should not be called when overwrite is declined"
    assert any(
        kind == "askyesno" for kind, *_ in mb.calls  # type: ignore[misc]
    ), "Expected overwrite confirmation prompt"


def test_run_writes_csv_windows_profile(
    convert_mod: types.ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Arrange: CSV ('quicken-windows') profile; Act: run_conversion; Assert: writer called & info shown."""
    # Arrange
    tab, mb = _make_tab(convert_mod)
    tab.in_path.set(r"C:\fake\input.qif")
    tab.out_path.set(r"C:\fake\out.csv")
    tab.emit_var.set("csv")
    tab.csv_profile.set("quicken-windows")
    tab.date_from.set("")  # no filters
    tab.date_to.set("")
    # input exists, output does not (no overwrite prompt)
    _patch_path_exists(
        monkeypatch, convert_mod, predicate=lambda p: p.endswith("input.qif")
    )
    _patch_helpers_passthrough(monkeypatch)  # ensure filters are deterministic
    _patch_qif_parser(monkeypatch, convert_mod, n_txns=2)
    calls: list[tuple[str, int, str]] = []
    _patch_csv_writers(monkeypatch, convert_mod, calls)
    # Act
    tab.run_conversion()
    # Assert
    assert any(c[0] == "writer_called" for c in calls), "CSV writer should be invoked"
    assert any(
        kind == "showinfo" for kind, *_ in mb.calls  # type: ignore[misc]
    ), "Expected completion info dialog"
