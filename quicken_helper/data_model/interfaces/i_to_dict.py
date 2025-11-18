# quicken_helper/data_model/interfacts/i_to_dict.py
from __future__ import annotations

from typing import Protocol, TypeAlias, runtime_checkable

RecursiveDictStr: TypeAlias = (
    str | dict[str, "RecursiveDictStr"] | list["RecursiveDictStr"]
)


@runtime_checkable
class IToDict(Protocol):
    def to_dict(self) -> dict[str, RecursiveDictStr]: ...
