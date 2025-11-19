from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


def _dict_list() -> List[Dict[str, Any]]:
    return []


def _sections_dict() -> Dict[str, List[Dict[str, Any]]]:
    return {}


@dataclass
class ParsedQIF:
    transactions: List[Dict[str, Any]] = field(default_factory=_dict_list)
    accounts: List[Dict[str, Any]] = field(default_factory=_dict_list)
    categories: List[Dict[str, Any]] = field(default_factory=_dict_list)
    memorized_payees: List[Dict[str, Any]] = field(default_factory=_dict_list)
    securities: List[Dict[str, Any]] = field(default_factory=_dict_list)
    business_list: List[Dict[str, Any]] = field(
        default_factory=_dict_list
    )  # classes/business
    payees: List[Dict[str, Any]] = field(default_factory=_dict_list)
    other_sections: Dict[str, List[Dict[str, Any]]] = field(
        default_factory=_sections_dict
    )
