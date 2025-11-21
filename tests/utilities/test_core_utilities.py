from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from quicken_helper.utilities import to_date


# ---------- _parse_qif_date ----------
@pytest.mark.parametrize(
    "raw,expect_iso",
    [
        ("12/31'24", "2024-12-31"),
        ("12/31/2024", "2024-12-31"),
        ("2024-12-31", "2024-12-31"),
        ("2024/12/31", "2024-12-31"),
    ],
)
def test__parse_qif_date_formats(raw: str, expect_iso: str) -> None:
    """Test to_date parses various QIF date formats correctly."""
    d = to_date(raw)
    assert d.isoformat() == expect_iso


def test__open_for_read_uses_builtins_open(
    monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test open_for_read uses builtins.open and returns readable file object.
    
    Policy compliance: No filesystem I/O, mocks builtins.open.
    """
    # Arrange
    from quicken_helper.utilities.core_util import open_for_read

    opened = {"called": False}
    expected = "hello world"

    class FakeReadable:
        def __enter__(self) -> FakeReadable:
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
            pass

        def read(self, *_: Any, **__: Any) -> str:
            return expected

    def fake_open(
        file: Any,
        mode: str = "r",
        encoding: str | None = None,
        newline: str | None = None,
        **kwargs: Any,
    ) -> FakeReadable:
        opened["called"] = True
        # basic sanity: _open_for_read should open in text mode by default
        assert "b" not in mode
        return FakeReadable()

    monkeypatch.setattr("builtins.open", fake_open, raising=True)
    p = Path("/mock/sample.data_model")  # Mock path - no actual file needed

    # Act
    with open_for_read(p) as f:  # type: ignore[attr-defined]
        data: str = f.read()  # type: ignore[no-untyped-call]

    # Assert
    assert opened["called"] is True, "Expected _open_for_read to call builtins.open"
    assert (
        data == expected
    ), "File-like object returned by _open_for_read should be readable"
