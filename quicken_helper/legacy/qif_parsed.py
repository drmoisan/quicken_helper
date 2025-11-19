from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _dict_list() -> list[dict[str, Any]]:
    return []


def _sections_dict() -> dict[str, list[dict[str, Any]]]:
    return {}


@dataclass
class ParsedQIF:
    transactions: list[dict[str, Any]] = field(default_factory=_dict_list)
    accounts: list[dict[str, Any]] = field(default_factory=_dict_list)
    categories: list[dict[str, Any]] = field(default_factory=_dict_list)
    memorized_payees: list[dict[str, Any]] = field(default_factory=_dict_list)
    securities: list[dict[str, Any]] = field(default_factory=_dict_list)
    business_list: list[dict[str, Any]] = field(
        default_factory=_dict_list
    )  # classes/business
    payees: list[dict[str, Any]] = field(default_factory=_dict_list)
    other_sections: dict[str, list[dict[str, Any]]] = field(
        default_factory=_sections_dict
    )
