# quicken_helper/data_model/interfaces/i_equatable.py
from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class IEquatable(Protocol):
    def __eq__(self, other: object) -> bool: ...
    def __hash__(self) -> int: ...
