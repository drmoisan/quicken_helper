from __future__ import annotations

from dataclasses import dataclass
from functools import total_ordering
from typing import TYPE_CHECKING

from quicken_helper.data_model.interfaces import IHeader, ITag, RecursiveDictStr

from .qif_header import QifHeader


@total_ordering
@dataclass
class QTag:
    """
    Represents an account in QIF format.
    """

    name: str = ""
    description: str = ""

    @property
    def header(self) -> IHeader:
        """
        Returns the type of the account.
        """
        h = QifHeader("!Type:Tag", "Tag list", "Tag")
        return h

    def emit_qif(self, with_header: bool = False) -> str:
        if with_header:
            return f"{self.header.code}\nN{self.name}\nD{self.description}\n^"
        return f"N{self.name}\nD{self.description}"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ITag):
            return False
        return self.name == other.name and self.header == other.header

    def __hash__(self) -> int:
        # Required if you want to use instances in sets/dicts and keep it consistent with __eq__
        return hash((self.name, self.header))

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, ITag):
            return NotImplemented
        return self.name < other.name

    def to_dict(self) -> dict[str, RecursiveDictStr]:
        return {
            "name": self.name,
            "description": self.description,
        }


if TYPE_CHECKING:
    _is_i_tag: type[ITag] = QTag
