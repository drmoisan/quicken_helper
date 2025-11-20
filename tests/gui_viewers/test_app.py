# tests/gui_viewers/test_app.py
"""
Lean App smoke test after removing shims from app.py.

We keep minimal tkinter + GUI tab stubs so quicken_helper.gui_viewers.app
can import & build without a real display. This file intentionally does NOT
test Convert/Merge/Probe functionality; those now have dedicated tests.
"""

from __future__ import annotations

import importlib
import sys
import types
from typing import Any

import pytest

# --------------------------
# Minimal tkinter stubs
# --------------------------


def _install_tk_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install minimal tkinter/ttk/font/messagebox stubs so App can import & run headlessly."""

    tk = types.ModuleType("tkinter")

    class Tk:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def geometry(self, *a: object, **k: object) -> None:
            pass

        def minsize(self, *a: object, **k: object) -> None:
            pass

        def option_add(self, *a: object, **k: object) -> None:
            pass

        def title(self, *a: object, **k: object) -> None:
            pass

        def mainloop(self, *a: object, **k: object) -> None:
            pass

    class StringVar:
        def __init__(self, value: str = "") -> None:
            self._v: str = value

        def get(self) -> str:
            return self._v

        def set(self, v: str) -> None:
            self._v = v

    class BooleanVar:
        def __init__(self, value: bool = False) -> None:
            self._v: bool = value

        def get(self) -> bool:
            return self._v

        def set(self, v: bool) -> None:
            self._v = v

    class Text:
        def __init__(self, *a: object, **k: object) -> None:
            self._buf: str = ""

        def get(self, s: object, e: object) -> str:
            return self._buf

        def insert(self, i: object, s: str) -> None:
            self._buf += s

        def delete(self, s: object, e: object) -> None:
            self._buf = ""

        def see(self, i: object) -> None:
            pass

    tk.Tk = Tk  # type: ignore[attr-defined]
    tk.StringVar = StringVar  # type: ignore[attr-defined]
    tk.BooleanVar = BooleanVar  # type: ignore[attr-defined]
    tk.Text = Text  # type: ignore[attr-defined]

    ttk = types.ModuleType("tkinter.ttk")

    class Frame:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def pack(self, *a: object, **k: object) -> None:
            pass

        def grid(self, *a: object, **k: object) -> None:
            pass

    class LabelFrame(Frame):
        pass

    class Button:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def grid(self, *a: object, **k: object) -> None:
            pass

    class Entry:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def grid(self, *a: object, **k: object) -> None:
            pass

    class Notebook(Frame):
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def add(self, *a: object, **k: object) -> None:
            pass

        def pack(self, *a: object, **k: object) -> None:
            pass

    class Style:
        def __init__(self, *a: object, **k: object) -> None:
            pass

        def theme_use(self, *a: object, **k: object) -> None:
            pass

        def configure(self, *a: object, **k: object) -> None:
            pass

        def map(self, *a: object, **k: object) -> None:
            pass

    ttk.Frame = Frame  # type: ignore[attr-defined]
    ttk.LabelFrame = LabelFrame  # type: ignore[attr-defined]
    ttk.Button = Button  # type: ignore[attr-defined]
    ttk.Entry = Entry  # type: ignore[attr-defined]
    ttk.Notebook = Notebook  # type: ignore[attr-defined]
    ttk.Style = Style  # type: ignore[attr-defined]

    filedialog = types.ModuleType("tkinter.filedialog")
    messagebox = types.ModuleType("tkinter.messagebox")

    def _noop(*a: object, **k: object) -> None:
        return None

    messagebox.showinfo = _noop  # type: ignore[attr-defined]
    messagebox.showerror = _noop  # type: ignore[attr-defined]
    messagebox.askyesno = lambda *a, **k: True  # type: ignore[attr-defined]

    font = types.ModuleType("tkinter.font")

    class _Font:
        def __init__(self, *a: object, **k: object) -> None:
            self._cfg: dict[str, Any] = {
                "family": "TkDefaultFont",
                "size": 10,
                "weight": "normal",
            }

        def cget(self, k: str) -> Any:
            return self._cfg.get(k)

        def configure(self, **k: Any) -> None:
            self._cfg.update(k)

    def nametofont(name: str) -> _Font:
        return _Font()

    font.Font = _Font  # type: ignore[attr-defined]
    font.nametofont = nametofont  # type: ignore[attr-defined]

    # Register stubs
    monkeypatch.setitem(sys.modules, "tkinter", tk)
    monkeypatch.setitem(sys.modules, "tkinter.ttk", ttk)
    monkeypatch.setitem(sys.modules, "tkinter.messagebox", messagebox)
    monkeypatch.setitem(sys.modules, "tkinter.filedialog", filedialog)
    monkeypatch.setitem(sys.modules, "tkinter.font", font)


# --------------------------
# GUI submodule stubs (ConvertTab / MergeTab / ProbeTab)
# --------------------------


def _install_gui_submodule_stubs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provide minimal stand-ins for GUI tabs so App wiring works without real UI."""

    # ConvertTab (accepts the new optional session param)
    convert_tab = types.ModuleType("quicken_helper.gui_viewers.convert_tab")

    class ConvertTab:
        def __init__(self, app: object, mb: object, session: object = None) -> None:
            self.app = app
            self.mb = mb
            self.session = session

    convert_tab.ConvertTab = ConvertTab  # type: ignore[attr-defined]
    monkeypatch.setitem(
        sys.modules, "quicken_helper.gui_viewers.convert_tab", convert_tab
    )

    # MergeTab
    merge_tab = types.ModuleType("quicken_helper.gui_viewers.merge_tab")

    class MergeTab:
        def __init__(self, *a: object, **k: object) -> None:
            pass

    merge_tab.MergeTab = MergeTab  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quicken_helper.gui_viewers.merge_tab", merge_tab)

    # ProbeTab
    probe_tab = types.ModuleType("quicken_helper.gui_viewers.probe_tab")

    class ProbeTab:
        def __init__(self, *a: object, **k: object) -> None:
            pass

    probe_tab.ProbeTab = ProbeTab  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quicken_helper.gui_viewers.probe_tab", probe_tab)


# --------------------------
# Fixture: import App with stubs
# --------------------------


@pytest.fixture
def app_mod(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import quicken_helper.gui_viewers.app with tkinter & GUI submodules stubbed."""
    _install_tk_stubs(monkeypatch)
    _install_gui_submodule_stubs(monkeypatch)

    # Clean import
    for key in list(sys.modules):
        if key.endswith(".app") and key.split(".")[-2] == "gui_viewers":
            sys.modules.pop(key, None)

    return importlib.import_module("quicken_helper.gui_viewers.app")


# --------------------------
# Tests
# --------------------------


def test_app_init_builds_tabs(app_mod: types.ModuleType) -> None:
    """App builds the Notebook and instantiates Convert/Merge/Probe tabs (no shim checks)."""
    App = app_mod.App
    app = App(messagebox_api=None)
    assert hasattr(app, "nb"), "Notebook should be constructed"
    assert hasattr(app, "convert_tab"), "ConvertTab should be constructed"
    assert hasattr(app, "merge_tab"), "MergeTab should be constructed"
    assert hasattr(app, "probe_tab"), "ProbeTab should be constructed"
