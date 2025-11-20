# tests/gui_viewers/test_category_popout.py
from __future__ import annotations

import sys
import types
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest

import quicken_helper.gui_viewers.category_popout as cp

# ---------- Stubs & fixtures ----------


@dataclass
class _FakeMB:
    calls: list[tuple[str, str, str]]

    def showinfo(self, title: str, message: str) -> None:
        self.calls.append(("showinfo", title, message))

    def showerror(self, title: str, message: str) -> None:
        self.calls.append(("showerror", title, message))


class _FakeSession:
    pass


@pytest.fixture(autouse=True)
def _install_mex_stub(  # type: ignore[reportUnusedFunction]
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None]:
    """Install a stubbed controllers.merge_excel inside the module under test."""
    mex = types.ModuleType("quicken_helper.controllers.merge_excel")
    # Provide deterministic values for tests
    mex.build_matched_only_txns = lambda session: ["t1", "t2"]  # type: ignore[attr-defined,misc]
    mex.extract_qif_categories = lambda txns: {"A", "B"}  # type: ignore[attr-defined,misc]
    mex.extract_excel_categories = lambda p: {"B", "C"}  # type: ignore[attr-defined,misc]

    # Ensure parent package exists
    pkg = sys.modules.setdefault(
        "quicken_helper.controllers", types.ModuleType("quicken_helper.controllers")
    )
    pkg.__path__ = getattr(pkg, "__path__", [])  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "quicken_helper.controllers.merge_excel", mex)

    # Rebind in the loaded module (since cp imported mex at module import time)
    monkeypatch.setattr(cp, "mex", mex, raising=True)
    yield


# ---------- Tests ----------


def test_compute_category_sets_returns_expected_sets(tmp_path: Path) -> None:
    session = _FakeSession()  # type: ignore[arg-type]
    xlsx = tmp_path / "x.xlsx"
    xlsx.write_text("")  # path existence not required by stub

    q, x = cp.compute_category_sets(session, xlsx)  # type: ignore[arg-type]
    assert q == {"A", "B"}
    assert x == {"B", "C"}


def test_open_normalize_modal_calls_mb_and_returns_sets(tmp_path: Path) -> None:
    session = _FakeSession()  # type: ignore[arg-type]
    xlsx = tmp_path / "x.xlsx"
    mb = _FakeMB(calls=[])

    out = cp.open_normalize_modal(None, session, xlsx, mb=mb, show_ui=False)  # type: ignore[arg-type]
    assert out == ({"A", "B"}, {"B", "C"})
    assert any(c[0] == "showinfo" for c in mb.calls)
