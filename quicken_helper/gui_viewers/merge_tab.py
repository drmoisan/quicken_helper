# quicken_helper/gui_viewers/merge_tab.py
from __future__ import annotations

import logging
import logging.config
import tkinter as tk
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from tkinter import filedialog, ttk
from typing import Any

from quicken_helper.controllers import match_excel as mex
from quicken_helper.controllers.data_session import DataSession
from quicken_helper.controllers.match_session import MatchSession

# from quicken_helper.qif_loader import load_transactions
from quicken_helper.controllers.qif_loader import load_transactions_protocol
from quicken_helper.data_model import EnumClearedStatus, ITransaction
from quicken_helper.data_model.excel import (
    map_group_to_excel_txn,
)
from quicken_helper.gui_viewers.category_popout import (
    open_normalize_modal as open_category_popout,
)
from quicken_helper.gui_viewers.helpers import fmt_excel_row, fmt_txn, set_text
from quicken_helper.gui_viewers.message_box_api import MessageBoxAPI

# import qif_item_key
from quicken_helper.utilities import LOGGING

logging.config.dictConfig(LOGGING)
log = logging.getLogger(__name__)


@dataclass
class _ListColumn:
    frame: ttk.LabelFrame
    listbox: tk.Listbox
    preview: tk.Text


class MergeTab(ttk.Frame):
    """Primary function: Excel ↔ QIF merge + manual matching + previews."""

    def __init__(
        self, master: tk.Misc, mb: MessageBoxAPI, session: DataSession | None = None
    ):
        """Initialize UI state, bind actions, and prepare empty `MatchSession`.

        Does not perform any I/O. File selection or drag-drop handlers call
        the loader methods to populate the session.

        Args:
            master: The parent Tkinter widget.
            mb: MessageBox API for showing dialogs.
            session: Optional DataSession for shared data access.
        """
        super().__init__(master)
        self.mb = mb
        self.session = session
        self._merge_session: MatchSession | None = None

        # Ensure test-visible lists always exist (even if load/refresh bails early)
        self.m_pairs: list = []
        self.m_unmatched_qif: list = []
        self.m_unmatched_excel: list = []

        self._build()

    def _build(self) -> None:
        self._init_state_vars()
        self._build_files_section()
        self._build_controls_section()
        self._build_actions_section()
        self._build_lists_section()  # internally builds the 3 columns via a reusable helper
        self._build_footer_section()
        self._build_info_section()
        self._bind_preview_events()

    def _build_list_column(
        self,
        parent: tk.Misc,
        title: str,
        export_slug: str,
    ) -> _ListColumn:
        lf = ttk.LabelFrame(parent, text=title)
        lf.pack(side="left", fill="both", expand=True, padx=4, pady=4)

        container = ttk.Frame(lf)
        container.pack(fill="both", expand=True)

        lbx = tk.Listbox(container, exportselection=False)
        lbx.pack(fill="both", expand=True, padx=4, pady=4)

        btns = ttk.Frame(container)
        btns.pack(fill="x", padx=4, pady=(0, 4))
        ttk.Button(
            btns,
            text="Export…",
            command=lambda: self._export_listbox(lbx, export_slug),
        ).pack(side="left")

        prev = tk.Text(container, height=8, wrap="word")
        prev.pack_forget()

        return _ListColumn(frame=lf, listbox=lbx, preview=prev)

    def _init_state_vars(self) -> None:
        self.m_qif_in = tk.StringVar()
        self.m_xlsx = tk.StringVar()
        self.m_qif_out = tk.StringVar()
        self.m_only_matched = tk.BooleanVar(value=False)
        self.m_preview_var = tk.BooleanVar(value=False)

    def _build_files_section(self) -> None:
        files = ttk.LabelFrame(self, text="Files")
        files.pack(fill="x", padx=8, pady=6)

        ttk.Label(files, text="Input QIF:").grid(row=0, column=0, sticky="w")
        ttk.Entry(files, textvariable=self.m_qif_in, width=90).grid(
            row=0, column=1, sticky="we", padx=5
        )
        ttk.Button(files, text="Browse…", command=self._m_browse_qif).grid(
            row=0, column=2
        )

        ttk.Label(files, text="Excel (.xlsx):").grid(row=1, column=0, sticky="w")
        ttk.Entry(files, textvariable=self.m_xlsx, width=90).grid(
            row=1, column=1, sticky="we", padx=5
        )
        ttk.Button(files, text="Browse…", command=self._m_browse_xlsx).grid(
            row=1, column=2
        )

        ttk.Label(files, text="Output QIF:").grid(row=2, column=0, sticky="w")
        ttk.Entry(files, textvariable=self.m_qif_out, width=90).grid(
            row=2, column=1, sticky="we", padx=5
        )
        ttk.Button(files, text="Browse…", command=self._m_browse_out).grid(
            row=2, column=2
        )

        files.columnconfigure(1, weight=1)

    def _build_controls_section(self) -> None:
        controls = ttk.Frame(self)
        controls.pack(anchor="w", padx=12, pady=(0, 6), fill="x")
        ttk.Checkbutton(
            controls, text="Output Only Matched Items", variable=self.m_only_matched
        ).pack(side="left")
        ttk.Checkbutton(
            controls,
            text="Preview Window",
            variable=self.m_preview_var,
            command=self._m_toggle_previews,
        ).pack(side="left", padx=(12, 0))

    def _build_actions_section(self) -> None:
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=8, pady=6)
        ttk.Button(actions, text="Load", command=self._m_load).pack(side="left")
        ttk.Button(actions, text="Auto-Match", command=self._m_auto_match).pack(
            side="left", padx=6
        )
        ttk.Button(
            actions,
            text="Normalize Categories",
            command=self.open_normalize_modal,  # normalize_cats_modal
        ).pack(side="left", padx=6)
        ttk.Button(
            actions, text="Apply Updates & Save", command=self._m_apply_and_save
        ).pack(side="right")

    def _build_lists_section(self) -> None:
        lists = ttk.Frame(self)
        lists.pack(fill="both", expand=True, padx=8, pady=6)

        # Build columns via reusable helper and attach to self
        left = self._build_list_column(lists, "Unmatched QIF items", "unmatched_qif")
        self.lbx_unqif, self.prev_unqif = left.listbox, left.preview

        mid = self._build_list_column(lists, "Matched pairs", "matched_pairs")
        self.lbx_pairs, self.prev_pairs = mid.listbox, mid.preview

        right = self._build_list_column(
            lists, "Unmatched Excel rows", "unmatched_excel"
        )
        self.lbx_unx, self.prev_unx = right.listbox, right.preview

    def _build_footer_section(self) -> None:
        foot = ttk.Frame(self)
        foot.pack(fill="x", padx=8, pady=6)
        ttk.Button(foot, text="Match Selected →", command=self._m_manual_match).pack(
            side="left"
        )
        ttk.Button(foot, text="Unmatch Selected", command=self._m_manual_unmatch).pack(
            side="left", padx=8
        )
        ttk.Button(foot, text="Why not matched?", command=self._m_why_not).pack(
            side="left", padx=8
        )

    def _build_info_section(self) -> None:
        infof = ttk.LabelFrame(self, text="Info")
        infof.pack(fill="x", padx=8, pady=6)
        self.txt_info = tk.Text(infof, height=6, wrap="word")
        self.txt_info.pack(fill="x", padx=8, pady=6)

    def _bind_preview_events(self) -> None:
        self.lbx_unqif.bind(
            "<<ListboxSelect>>", lambda e: self._m_update_preview("unqif")
        )
        self.lbx_pairs.bind(
            "<<ListboxSelect>>", lambda e: self._m_update_preview("pairs")
        )
        self.lbx_unx.bind("<<ListboxSelect>>", lambda e: self._m_update_preview("unx"))

    # --------- Protocol→dict adapters (temporary during migration) ---------
    @staticmethod
    def _format_date(d: date) -> str:
        # Legacy merge pipeline expects string dates; standardize as MM/DD/YYYY
        return f"{d.month:02d}/{d.day:02d}/{d.year:04d}"

    @staticmethod
    def _cleared_to_char(val: Any) -> str:
        """
        Map a cleared-like value to a single display char without assuming the value is hashable.
        Accepts:
          - Enum-like (has .name)
          - strings ("yes", "reconciled", "no", "c", "r", etc.)
          - ints (0/1/2) or bools
          - None
        """
        if val is None:
            name = ""
        elif isinstance(val, str):
            name = val
        else:
            # Enum-like or other object: prefer .name; fallback to str()
            name_attr: str | None = getattr(val, "name", None)
            if name_attr is None:
                # Some stubs stringify to something useful, e.g. "EnumClearedStatus.NO"
                name = str(val)
            else:
                name = name_attr
        name = (name or "").strip().upper()

        # Common “uncleared/unknown” cases
        if name in {"", "NO", "UNKNOWN", "UNCLEARED", "FALSE", "0"}:
            return " "
        # “cleared”
        if name in {"YES", "CLEARED", "TRUE", "C", "1"}:
            return "c"
        # “reconciled”
        if name in {"RECONCILED", "R", "2"}:
            return "R"

        # Fallback to blank
        return " "

    @classmethod
    def _txn_to_dict(cls, t: ITransaction) -> dict[str, Any]:
        """Shape a protocol transaction for display (robust to missing optional attrs)."""
        category = getattr(t, "category", "") or ""
        tag = getattr(t, "tag", "") or ""
        if tag:
            category = f"{category}/{tag}" if category else tag
        return {
            "date": cls._format_date(getattr(t, "date", date.today())),
            "amount": str(getattr(t, "amount", "")),
            "payee": getattr(t, "payee", "") or "",
            "memo": getattr(t, "memo", "") or "",
            "category": category,
            "checknum": getattr(t, "action_chk", None),
            "cleared": cls._cleared_to_char(
                getattr(t, "cleared", EnumClearedStatus.UNKNOWN)
            ),
            "splits": [
                {
                    "amount": str(getattr(s, "amount", "")),
                    "category": getattr(s, "category", "") or "",
                    "memo": getattr(s, "memo", "") or "",
                }
                for s in (getattr(t, "splits", None) or [])
            ],
        }

    # ---------- file pickers ----------
    def _m_browse_qif(self):
        p = filedialog.askopenfilename(
            title="Select input QIF",
            filetypes=[("QIF files", "*.qif"), ("All files", "*.*")],
        )
        if p:
            self.m_qif_in.set(p)
            if not self.m_qif_out.get().strip():
                self.m_qif_out.set(
                    str(Path(p).with_name(Path(p).stem + "_updated.qif"))
                )

    def _m_browse_xlsx(self):
        p = filedialog.askopenfilename(
            title="Select Excel workbook",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
        )
        if p:
            self.m_xlsx.set(p)

    def _m_browse_out(self):
        p = filedialog.asksaveasfilename(
            title="Select output QIF",
            defaultextension=".qif",
            filetypes=[("QIF files", "*.qif"), ("All files", "*.*")],
        )
        if p:
            self.m_qif_out.set(p)

    # ---------- actions ----------
    def _m_load(self) -> None:
        """Load inputs and build a session without auto-matching."""
        try:
            qif_in = Path(self.m_qif_in.get().strip())
            xlsx = Path(self.m_xlsx.get().strip())

            if not qif_in.exists():
                self.mb.showerror("Error", "Please choose a valid input QIF.")
                return
            if not xlsx.exists():
                self.mb.showerror("Error", "Please choose a valid Excel (.xlsx).")
                return

            # Bank/Excel side: prefer cached DataSession if available
            if self.session:
                bank_txns = self.session.load_qif(qif_in)
                excel_txns = self.session.load_excel(xlsx)
                rows = self.session.excel_rows or []
            else:
                # Bank side: already ITransaction via loader
                bank_txns = load_transactions_protocol(qif_in)
                # Excel side: rows -> groups -> ITransaction (via adapter)
                rows = mex.load_excel_rows(xlsx)
                groups = mex.group_excel_rows(rows)
                excel_txns = [map_group_to_excel_txn(g) for g in groups]

            # Build session but DO NOT auto-match yet
            sess = MatchSession(bank_txns, excel_txns)

            # Publish session and refresh UI
            self._merge_session = sess
            self._m_refresh_lists()
            self._m_info(
                "Loaded "
                f"{len(bank_txns)} QIF transactions and "
                f"{len(excel_txns)} Excel groups (as transactions) "
                f"({len(rows)} split rows).\n"
                "Ready to auto-match: click the Auto-Match button."
            )
        except Exception as e:
            # Keep the test-visible failure simple
            self._merge_session = None
            self.mb.showerror("Error", f"{e}")

    def _m_auto_match(self) -> None:
        """Run auto-matching on the currently loaded session."""
        try:
            s = self._merge_session
            if not s:
                self.mb.showerror("Error", "No session loaded. Click 'Load' first.")
                return
            s.auto_match()
            self._m_refresh_lists()
            self._m_info(
                f"Matched pairs: {len(s.pairs)} | "
                f"Unmatched QIF: {len(s.unmatched_bank)} | "
                f"Unmatched Excel: {len(s.unmatched_excel)}"
            )
        except Exception as e:
            self.mb.showerror("Error", f"{e}")

    def _m_manual_match(self):
        s = self._merge_session
        if not s:
            self.mb.showerror("Error", "No session loaded.")
            return
        bi = self._m_selected_unqif_index()
        ei = self._m_selected_unx_index()
        if bi is None or ei is None:
            self.mb.showerror(
                "Error", "Select one QIF item and one Excel item to match."
            )
            return
        s.manual_match(bank_index=bi, excel_index=ei)
        self._m_info("Matched.")
        self._m_refresh_lists()

    def _m_manual_unmatch(self):
        s = self._merge_session
        if not s:
            return

        # If a pair is selected, unmatch by its bank index
        sel = self.lbx_pairs.curselection()
        if sel:
            try:
                bi, ei, _b, _e = self._pairs_sorted[sel[0]]
            except Exception:
                b, e = s.pairs[sel[0]]
                bi = s.bank_txns.index(b)
            s.manual_unmatch(bank_index=bi)
            self._m_info("Unmatched selected pair.")
            self._m_refresh_lists()
            return

        # Otherwise, unmatch by whichever unmatched list has selection
        bi = self._m_selected_unqif_index()
        if bi is not None:
            s.manual_unmatch(bank_index=bi)
            self._m_info("Unmatched QIF item.")
            self._m_refresh_lists()
            return

        ei = self._m_selected_unx_index()
        if ei is not None:
            s.manual_unmatch(excel_index=ei)
            self._m_info("Unmatched Excel item.")
            self._m_refresh_lists()
            return

        self.mb.showinfo("Info", "Nothing selected to unmatch.")

    def _m_apply_and_save(self):
        try:
            s = self._merge_session
            if not s:
                self.mb.showerror("Error", "No session loaded. Click 'Load' first.")
                return
            qif_out = Path(self.m_qif_out.get().strip())
            if not qif_out:
                self.mb.showerror("Error", "Please choose an output QIF file.")
                return
            if qif_out.exists():
                if not self.mb.askyesno(
                    "Confirm Overwrite",
                    f"Output QIF already exists:\n\n{qif_out}\n\nOverwrite?",
                ):
                    return
            # Copy Excel splits onto matched bank txns (protocol objects)
            mex.apply_excel_splits(s, clear_top_category=True)
            # Choose what to write (matched-only vs all bank)
            txns_to_write = (
                mex.build_matched_only_txns(s)
                if self.m_only_matched.get()
                else s.bank_txns
            )

            # Emit QIF via the ITransaction emitter
            qif_out.parent.mkdir(parents=True, exist_ok=True)
            with open(qif_out, "w", encoding="utf-8") as fp:
                mex.emit_qif_transactions(txns_to_write, fp)

            self._m_info(f"Updates applied. Wrote updated QIF:\n{qif_out}")
            self.mb.showinfo("Done", f"Updated QIF written:\n{qif_out}")
        except Exception as e:
            self.mb.showerror("Error", str(e))

    def _m_info(self, msg: str):
        try:
            self.txt_info.delete("1.0", "end")
            self.txt_info.insert("end", msg)
        except Exception:
            try:
                self.mb.showinfo("Info", msg)
            except Exception:
                pass

    def _export_listbox(self, lb: tk.Listbox, default_tag: str):
        """Export the current strings shown in a Listbox to a file (txt or csv)."""
        items = lb.get(0, "end")
        if not items:
            self.mb.showinfo("Export", f"No items to export from '{default_tag}'.")
            return

        path = filedialog.asksaveasfilename(
            title=f"Export {default_tag}",
            initialfile=f"{default_tag}.txt",
            defaultextension=".txt",
            filetypes=[
                ("Text files", "*.txt"),
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                for row in items:
                    f.write(str(row) + "\n")
            self.mb.showinfo("Export", f"Exported {len(items)} items to:\n{path}")
        except Exception as e:
            self.mb.showerror("Export Error", str(e))

    # Backward-compatible private name (kept; just forwards)

    def open_normalize_modal(self):
        """Open the Normalize Categories popout (delegated to category_popout)."""
        try:
            if not getattr(self, "_merge_session", None):
                self.mb.showerror("Error", "Load data first.")
                return
            xlsx_path = Path(self.m_xlsx.get().strip())
            open_category_popout(
                self, self._merge_session, xlsx_path, mb=self.mb, show_ui=False
            )
        except Exception as e:
            # Keep UI resilient
            self.mb.showerror("Error", f"{e}")

    def _m_normalize_categories(self):
        """Toolbar/Actions handler: Normalize Categories."""
        try:
            if not getattr(self, "_merge_session", None):
                self.mb.showerror("Error", "Load data first.")
                return
            xlsx_path = Path(self.m_xlsx.get().strip())
            open_category_popout(
                self, self._merge_session, xlsx_path, mb=self.mb, show_ui=False
            )
        except Exception as e:
            self.mb.showerror("Error", f"{e}")

    # def _m_normalize_categories(self):
    #     return self.open_normalize_modal()

    # ---------- list/preview plumbing ----------
    def _m_refresh_lists(self) -> None:
        # Clear listboxes
        self.lbx_pairs.delete(0, "end")
        self.lbx_unqif.delete(0, "end")
        self.lbx_unx.delete(0, "end")

        s = getattr(self, "_merge_session", None)
        # Initialize caches and test-visible mirrors
        self._pairs_sorted = []
        self._unqif_sorted = []
        self._unx_sorted = []
        self.m_pairs = []
        self.m_unmatched_qif = []
        self.m_unmatched_excel = []

        if not s:
            return

        # ----- Matched pairs -----
        try:
            # Stable sort by (bank date, excel date, bank amount) for deterministic UI/tests
            def _pair_key(
                t: tuple[ITransaction, ITransaction],
            ) -> tuple[str, str, str]:
                b, e = t
                b_d = getattr(b, "date", None)
                e_d = getattr(e, "date", None)
                b_ds = b_d.isoformat() if b_d else ""
                e_ds = e_d.isoformat() if e_d else ""
                return (b_ds, e_ds, str(getattr(b, "amount", "")))

            pairs_sorted = sorted(s.pairs, key=_pair_key)

            for b, e in pairs_sorted:
                # Map back to indices for later manual unmatch ops
                try:
                    bi = s.bank_txns.index(b)
                except ValueError:
                    bi = -1
                try:
                    ei = s.excel_txns.index(e)
                except ValueError:
                    ei = -1

                self._pairs_sorted.append((bi, ei, b, e))
                self.m_pairs.append((b, e))

                label = (
                    f"{getattr(b, 'date', None).isoformat() if getattr(b, 'date', None) else ''} "
                    f"{getattr(b, 'amount', '')} — {getattr(b, 'payee', '')}  "
                    f"↔  Excel[{getattr(e, 'id', '')}] "
                    f"{getattr(e, 'date', None).isoformat() if getattr(e, 'date', None) else ''} "
                    f"{getattr(e, 'amount', '')} | "
                    f"{len(getattr(e, 'splits', []) or [])} split(s)"
                )
                self.lbx_pairs.insert("end", label)
        except Exception as e:
            log.exception("Operation failed: %s", e)
            # Keep UI resilient; leave pairs empty on error
            pass

        # ----- Unmatched QIF (bank side) -----
        try:

            def _bank_key(t: ITransaction) -> tuple[str, str, str]:
                d = getattr(t, "date", None)
                ds = d.isoformat() if d else ""
                return (ds, str(getattr(t, "amount", "")), getattr(t, "payee", ""))

            for b in sorted(s.unmatched_bank, key=_bank_key):
                try:
                    bi = s.bank_txns.index(b)
                except ValueError:
                    bi = -1
                self._unqif_sorted.append((bi, b))
                self.m_unmatched_qif.append(b)
                self.lbx_unqif.insert(
                    "end",
                    f"{getattr(b, 'date', None).isoformat() if getattr(b, 'date', None) else ''} "
                    f"{getattr(b, 'amount', '')} — {getattr(b, 'payee', '')}",
                )
        except Exception as e:
            log.exception("Operation failed: %s", e)
            pass

        # ----- Unmatched Excel (excel side) -----
        try:

            def _excel_key(t: ITransaction) -> tuple[str, str, str]:
                """Deterministic sort key for Excel-side ITransaction objects."""
                d = getattr(t, "date", None)
                ds = d.isoformat() if d else ""
                # amount may be Decimal; stringify for consistent tuple ordering
                try:
                    amt = str(getattr(t, "amount", ""))
                except Exception:
                    amt = ""
                payee = getattr(t, "payee", "") or ""
                return (ds, amt, payee)

            for e in sorted(s.unmatched_excel, key=_excel_key):
                try:
                    ei = s.excel_txns.index(e)
                except ValueError:
                    ei = -1
                self._unx_sorted.append((ei, e))
                self.m_unmatched_excel.append(e)
                self.lbx_unx.insert(
                    "end",
                    f"Excel[{getattr(e, 'id', '')}] "
                    f"{getattr(e, 'date', None).isoformat() if getattr(e, 'date', None) else ''} "
                    f"{getattr(e, 'amount', '')} | "
                    f"{len(getattr(e, 'splits', []) or [])} split(s)",
                )
        except Exception as e:
            log.exception("Operation failed: %s", e)
            pass

        # ----- Seed previews if the toggle is on -----
        if self.m_preview_var.get():
            try:
                # Unmatched QIF preview
                if self._unqif_sorted:
                    _bi, b = self._unqif_sorted[0]
                    set_text(
                        self.prev_unqif,
                        fmt_txn(
                            {
                                "date": (
                                    getattr(b, "date", None).isoformat()
                                    if getattr(b, "date", None)
                                    else ""
                                ),
                                "amount": str(getattr(b, "amount", "")),
                                "payee": getattr(b, "payee", "") or "",
                                "category": getattr(b, "category", "") or "",
                                "memo": getattr(b, "memo", "") or "",
                            }
                        ),
                    )
                # Unmatched Excel preview
                if self._unx_sorted:
                    _ei, e = self._unx_sorted[0]
                    first = (getattr(e, "splits", None) or [None])[0]
                    set_text(
                        self.prev_unx,
                        fmt_excel_row(
                            {
                                "TxnID": getattr(e, "id", "") or "",
                                "Date": (
                                    getattr(e, "date", None).isoformat()
                                    if getattr(e, "date", None)
                                    else ""
                                ),
                                "Total Amount": str(getattr(e, "amount", "")),
                                "Split Count": len(getattr(e, "splits", []) or []),
                                "First Item": (
                                    getattr(first, "memo", "") if first else ""
                                ),
                                "First Category": (
                                    getattr(first, "category", "") if first else ""
                                ),
                                "First Rationale": getattr(e, "memo", "") or "",
                            }
                        ),
                    )
                # First pair preview
                if self._pairs_sorted:
                    _bi, _ei, b, e = self._pairs_sorted[0]
                    excel_view = {
                        "TxnID": getattr(e, "id", "") or "",
                        "Date": (
                            getattr(e, "date", None).isoformat()
                            if getattr(e, "date", None)
                            else ""
                        ),
                        "Total Amount": str(getattr(e, "amount", "")),
                        "Split Count": len(getattr(e, "splits", []) or []),
                        "First Item": (
                            getattr(
                                (getattr(e, "splits", None) or [None])[0], "memo", ""
                            )
                            if getattr(e, "splits", None)
                            else ""
                        ),
                        "First Category": (
                            getattr(
                                (getattr(e, "splits", None) or [None])[0],
                                "category",
                                "",
                            )
                            if getattr(e, "splits", None)
                            else ""
                        ),
                        "First Rationale": getattr(e, "memo", "") or "",
                    }
                    qif_view = {
                        "date": (
                            getattr(b, "date", None).isoformat()
                            if getattr(b, "date", None)
                            else ""
                        ),
                        "amount": str(getattr(b, "amount", "")),
                        "payee": getattr(b, "payee", "") or "",
                        "category": getattr(b, "category", "") or "",
                        "memo": getattr(b, "memo", "") or "",
                    }
                    set_text(
                        self.prev_pairs,
                        "[Excel]\n"
                        + fmt_excel_row(excel_view)
                        + "\n\n[QIF]\n"
                        + fmt_txn(qif_view),
                    )
            except Exception:
                # Preview is non-critical; ignore errors to keep UI stable
                pass

    def _m_selected_unqif_index(self) -> int | None:
        if not getattr(self, "_unqif_sorted", None):
            return None
        sel = self.lbx_unqif.curselection()
        if not sel:
            return None
        # stored as (bank_index, txn)
        bi, _ = self._unqif_sorted[sel[0]]
        return bi

    def _m_selected_unx_index(self) -> int | None:
        if not getattr(self, "_unx_sorted", None):
            return None
        sel = self.lbx_unx.curselection()
        if not sel:
            return None
        # stored as (excel_index, txn)
        ei, _ = self._unx_sorted[sel[0]]
        return ei

    def _m_why_not(self):
        s = self._merge_session
        if not s:
            return
        bi = self._m_selected_unqif_index()
        if bi is None:
            self.mb.showinfo("Info", "Pick one unmatched QIF item to explain.")
            return
        self._m_info(s.nonmatch_reason(bank_index=bi))

    def _m_toggle_previews(self):
        show = bool(self.m_preview_var.get())
        for w in (self.prev_unqif, self.prev_pairs, self.prev_unx):
            try:
                if show:
                    w.pack(fill="x", padx=4, pady=(0, 4))
                else:
                    w.pack_forget()
            except Exception:
                pass
        if show:
            self._m_update_preview("unqif")
            self._m_update_preview("pairs")
            self._m_update_preview("unx")

    def _m_update_preview(self, which: str):
        if not self.m_preview_var.get():
            return
        try:
            if which == "unqif":
                idxs = self.lbx_unqif.curselection()
                if not idxs:
                    set_text(self.prev_unqif, "")
                    return
                _bi, b = self._unqif_sorted[idxs[0]]
                set_text(
                    self.prev_unqif,
                    fmt_txn(
                        {
                            "date": b.date.isoformat(),
                            "amount": str(getattr(b, "amount", "")),
                            "payee": getattr(b, "payee", ""),
                            "category": getattr(b, "category", ""),
                            "memo": getattr(b, "memo", ""),
                        }
                    ),
                )

            elif which == "unx":
                idxs = self.lbx_unx.curselection()
                if not idxs:
                    set_text(self.prev_unx, "")
                    return
                _ei, e = self._unx_sorted[idxs[0]]
                first = (e.splits or [None])[0]
                set_text(
                    self.prev_unx,
                    fmt_excel_row(
                        {
                            "TxnID": getattr(e, "id", ""),
                            "Date": e.date.isoformat(),
                            "Total Amount": getattr(e, "amount", ""),
                            "Split Count": len(e.splits or []),
                            "First Item": getattr(first, "memo", "") if first else "",
                            "First Category": (
                                getattr(first, "category", "") if first else ""
                            ),
                            "First Rationale": getattr(e, "memo", ""),
                        }
                    ),
                )

            elif which == "pairs":
                idxs = self.lbx_pairs.curselection()
                if not idxs:
                    set_text(self.prev_pairs, "")
                    return
                _bi, _ei, b, e = self._pairs_sorted[idxs[0]]
                excel_row = {
                    "TxnID": getattr(e, "id", ""),
                    "Date": e.date.isoformat(),
                    "Total Amount": getattr(e, "amount", ""),
                    "Split Count": len(e.splits or []),
                    "First Item": (
                        getattr((e.splits or [None])[0], "memo", "") if e.splits else ""
                    ),
                    "First Category": (
                        getattr((e.splits or [None])[0], "category", "")
                        if e.splits
                        else ""
                    ),
                    "First Rationale": getattr(e, "memo", ""),
                }
                qif_tx = {
                    "date": b.date.isoformat(),
                    "amount": str(getattr(b, "amount", "")),
                    "payee": getattr(b, "payee", ""),
                    "category": getattr(b, "category", ""),
                    "memo": getattr(b, "memo", ""),
                }
                set_text(
                    self.prev_pairs,
                    "[Excel]\n"
                    + fmt_excel_row(excel_row)
                    + "\n\n[QIF]\n"
                    + fmt_txn(qif_tx),
                )
        except Exception as e:
            try:
                self._m_info(f"Preview error: {e}")
            except Exception:
                pass
