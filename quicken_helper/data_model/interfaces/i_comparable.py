# quicken_helper/data_model/interfaces/i_comparable.py
from __future__ import annotations

from functools import total_ordering
from typing import Protocol, runtime_checkable


@total_ordering
@runtime_checkable
class IComparable(Protocol):
    def __eq__(self, other: object) -> bool: ...
    def __lt__(self, other: object) -> bool: ...
