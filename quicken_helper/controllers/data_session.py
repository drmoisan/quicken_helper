# quicken_helper/controllers/data_session.py
from __future__ import annotations

import logging
import logging.config
from dataclasses import dataclass, field
from pathlib import Path

from quicken_helper.controllers import match_excel as mex
from quicken_helper.controllers.qif_loader import load_transactions_protocol
from quicken_helper.data_model.excel import (
    ExcelRow,
    ExcelTransaction,
    ExcelTxnGroup,
    map_group_to_excel_txn,
)
from quicken_helper.data_model.interfaces import ITransaction
from quicken_helper.utilities import LOGGING

logging.config.dictConfig(LOGGING)
log = logging.getLogger(__name__)


def _empty_txn_list() -> list[ITransaction]:
    return []


def _empty_excel_row_list() -> list[ExcelRow]:
    return []


def _empty_excel_group_list() -> list[ExcelTxnGroup]:
    return []


def _empty_excel_txn_list() -> list[ExcelTransaction]:
    return []


@dataclass
class DataSession:
    """
    Centralizes file loading and in-memory data for GUI tabs.

    Responsibilities:
    • Load and memoize QIF transactions once per path.
    • Load and memoize Excel rows/groups and expose Excel-side transactions.
    • Provide lightweight invalidation when file paths change.
    """

    qif_path: Path | None = None
    qif_txns: list[ITransaction] = field(default_factory=_empty_txn_list)

    excel_path: Path | None = None
    excel_rows: list[ExcelRow] = field(default_factory=_empty_excel_row_list)
    excel_groups: list[ExcelTxnGroup] = field(default_factory=_empty_excel_group_list)
    excel_txns: list[ExcelTransaction] = field(default_factory=_empty_excel_txn_list)

    def load_qif(self, path: Path, *, encoding: str = "utf-8") -> list[ITransaction]:
        path = Path(path)
        if self.qif_path != path or not self.qif_txns:
            log.info("Loading QIF: %s", path)
            self.qif_txns = list(load_transactions_protocol(path, encoding=encoding))
            self.qif_path = path
            log.debug("Loaded %d transactions from %s", len(self.qif_txns), path)
        else:
            log.debug(
                "Reusing cached QIF transactions for %s (%d txns)",
                path,
                len(self.qif_txns),
            )
        return self.qif_txns

    def load_excel(self, path: Path) -> list[ExcelTransaction]:
        path = Path(path)
        if self.excel_path != path or not self.excel_txns:
            log.info("Loading Excel: %s", path)
            rows = mex.load_excel_rows(path)
            groups = mex.group_excel_rows(rows)
            txns = [map_group_to_excel_txn(g) for g in groups]
            self.excel_path = path
            self.excel_rows = rows
            self.excel_groups = groups
            self.excel_txns = txns
            log.debug(
                "Loaded %d rows → %d groups → %d txns",
                len(rows),
                len(groups),
                len(txns),
            )
        else:
            log.debug(
                "Reusing cached Excel data for %s (%d txns)", path, len(self.excel_txns)
            )
        return self.excel_txns
