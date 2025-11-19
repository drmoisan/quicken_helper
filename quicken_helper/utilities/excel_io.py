"""Typed helpers for working with Excel inputs."""

from __future__ import annotations

from typing import Any

import pandas as pd
from pandas import DataFrame

ExcelInput = Any  # Accept wide range: str, Path, file-like, etc.


def read_excel_df(
    io: ExcelInput, *, sheet_name: int | str = 0, **kwargs: Any
) -> DataFrame:
    """
    Read an Excel file into a DataFrame while keeping tests easy to stub.

    The helper mirrors ``pandas.read_excel`` but catches the common situation
    where a monkeypatched function only accepts the path argument (no kwargs).
    In that case we retry without ``sheet_name``/kwargs.
    """

    pd_any: Any = pd
    try:
        return pd_any.read_excel(io, sheet_name=sheet_name, **kwargs)
    except TypeError as exc:
        if "sheet_name" in str(exc) and not kwargs:
            return pd_any.read_excel(io)
        raise
