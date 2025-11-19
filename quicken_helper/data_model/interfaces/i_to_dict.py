# quicken_helper/data_model/interfacts/i_to_dict.py
from __future__ import annotations

from typing import Protocol, runtime_checkable

type RecursiveDictStr = (str | dict[str, "RecursiveDictStr"] | list["RecursiveDictStr"])


@runtime_checkable
class IToDict(Protocol):
    def to_dict(self) -> dict[str, RecursiveDictStr]: ...
