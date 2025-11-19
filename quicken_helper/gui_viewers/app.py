# quicken_helper/gui_viewers/app.py
from __future__ import annotations

import logging
import logging.config
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk
from types import SimpleNamespace
from typing import Any, cast

from quicken_helper.controllers.data_session import DataSession
from quicken_helper.gui_viewers.convert_tab import ConvertTab

# project modules
from quicken_helper.gui_viewers.merge_tab import MergeTab
from quicken_helper.gui_viewers.probe_tab import ProbeTab
from quicken_helper.utilities import LOGGING

from .message_box_api import MessageBoxAPI
from .scaling import apply_global_font_scaling, detect_system_font_scale

logging.config.dictConfig(LOGGING)
log = logging.getLogger(__name__)


class App(tk.Tk):
    """
    Top-level window that hosts three tabs.
    For test-compatibility, we expose a few legacy attributes and methods.
    """

    def __init__(self, messagebox_api: MessageBoxAPI | None = None):
        """Initialize the main application window.

        Args:
            messagebox_api: Optional MessageBox API for dependency injection.
                           If None, uses standard tkinter messagebox functions.
        """
        super().__init__()
        # NEW: auto font scaling
        try:
            system_scaling: float = detect_system_font_scale()
            apply_global_font_scaling(self, system_scaling)
        except Exception:
            pass

        # --- Notebook (tab) styling for better visibility and selected color ---
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")  # clam respects custom colors on Windows/macOS
        except Exception:
            pass

        # Base font → slightly larger & bold for tabs
        try:
            base = tkfont.nametofont("TkDefaultFont")
            tab_font = tkfont.Font(
                self,
                family=base.cget("family"),
                size=max(12, int(base.cget("size")) + 2),
                weight="bold",
            )
        except Exception:
            tab_font = ("Segoe UI", 12, "bold")

        # Define a custom Notebook style so we can target its Tab style precisely
        cast("Any", self.style).configure(
            "Custom.TNotebook",
            background="#d1d5db",
            borderwidth=2,
            relief="ridge",
            tabmargins=(12, 6, 12, 0),
        )

        # Tab base (unselected) appearance
        cast("Any", self.style).configure(
            "Custom.TNotebook.Tab",
            font=tab_font,
            padding=(18, 10),
            borderwidth=2,
            relief="raised",
            background="#e5e7eb",  # light gray when not selected
            foreground="black",
        )

        # State-driven colors: selected and hover
        cast("Any", self.style).map(
            "Custom.TNotebook.Tab",
            background=[
                ("selected", "#2563eb"),  # vivid blue when selected
                ("active", "#3b82f6"),  # lighter blue on hover
                ("!selected", "#e5e7eb"),
            ],
            foreground=[
                ("selected", "white"),
                ("active", "white"),
                ("!selected", "black"),
            ],
        )

        # Apply the custom style to your Notebook
        # If you've already created it earlier, set the style attribute:
        #   self.nb.configure(style="Custom.TNotebook")
        # If you're creating it now, do:
        #   self.nb = ttk.Notebook(self, style="Custom.TNotebook")
        try:
            self.nb.configure(style="Custom.TNotebook")
        except Exception:
            pass

        # Dependency-injected messagebox wrapper; calls module functions at call time
        self.mb: MessageBoxAPI = cast(
            "MessageBoxAPI",
            (
                messagebox_api
                if messagebox_api is not None
                else SimpleNamespace(
                    showinfo=messagebox.showinfo,
                    showerror=messagebox.showerror,
                    askyesno=messagebox.askyesno,
                )
            ),
        )
        self.title("QIF Tools")
        self.geometry("980x720")
        self.minsize(920, 640)

        self.nb = ttk.Notebook(self)
        self.nb.pack(fill="both", expand=True)

        # after: self.nb = ttk.Notebook(self); self.nb.pack(...)
        # Build tabs (inject messagebox wrapper)
        self.session = DataSession()
        self.convert_tab = ConvertTab(self, self.mb, session=self.session)
        self.merge_tab = MergeTab(self, self.mb, session=self.session)
        self.probe_tab = ProbeTab(self, self.mb)

        # NOTEBOOK ORDER (Merge first, per your preference)
        self.nb.add(self.merge_tab, text="Excel ↔ QIF Merge")
        self.nb.add(self.convert_tab, text="Convert (QIF → CSV/QIF)")
        self.nb.add(self.probe_tab, text="QDX Probe")


if __name__ == "__main__":
    app = App()
    app.mainloop()
