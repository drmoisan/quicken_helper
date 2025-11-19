"""Tkinter widget protocols and typed helper functions for strict type checking.

This module provides:
1. Protocol definitions for common Tkinter widgets (Listbox, Text, Entry, etc.)
2. Type-safe pack() helper functions that accept keyword arguments properly
3. Common Tkinter types and aliases

These protocols and helpers ensure pyright strict mode passes without reportArgumentType
errors when using Tkinter widgets.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict, runtime_checkable

# ============================================================================
# Widget Protocols
# ============================================================================


@runtime_checkable
class ListboxProtocol(Protocol):
    """Protocol for Tkinter Listbox widget operations."""

    def delete(self, first: int | str, last: int | str | None = None) -> None:
        """Delete items from the listbox."""
        ...

    def get(
        self, first: int | str, last: int | str | None = None
    ) -> tuple[str, ...] | str:
        """Get items from the listbox."""
        ...

    def insert(self, index: int | str, *elements: str) -> None:
        """Insert items into the listbox."""
        ...

    def curselection(self) -> tuple[int, ...]:
        """Return tuple of indices of currently selected items."""
        ...

    def bind(self, sequence: str | None, func: Any, add: str | None = None) -> str:
        """Bind an event handler."""
        ...


@runtime_checkable
class TextProtocol(Protocol):
    """Protocol for Tkinter Text widget operations."""

    def delete(self, index1: str, index2: str | None = None) -> None:
        """Delete text from the widget."""
        ...

    def insert(self, index: str, chars: str, *args: Any) -> None:
        """Insert text into the widget."""
        ...

    def configure(self, **kwargs: Any) -> Any:
        """Configure widget options."""
        ...

    def pack(self, **kwargs: Any) -> None:
        """Pack the widget."""
        ...

    def pack_forget(self) -> None:
        """Unpack the widget."""
        ...


@runtime_checkable
class EntryProtocol(Protocol):
    """Protocol for Tkinter Entry widget operations."""

    def get(self) -> str:
        """Get the entry's value."""
        ...

    def delete(self, first: int | str, last: int | str | None = None) -> None:
        """Delete text from the entry."""
        ...

    def insert(self, index: int | str, string: str) -> None:
        """Insert text into the entry."""
        ...


# ============================================================================
# Pack Options TypedDict
# ============================================================================


class PackOptions(TypedDict, total=False):
    """Type-safe dictionary for Tkinter pack() options.

    This allows passing pack options as **kwargs while maintaining type safety.
    All fields are optional (total=False).
    """

    side: Literal["left", "right", "top", "bottom"]
    fill: Literal["none", "x", "y", "both"]
    expand: bool | Literal[0, 1]
    anchor: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"]
    padx: int | tuple[int, int]
    pady: int | tuple[int, int]
    ipadx: int
    ipady: int


# ============================================================================
# Type-Safe Pack Helpers
# ============================================================================


def pack_widget(
    widget: Any,
    *,
    side: Literal["left", "right", "top", "bottom"] | None = None,
    fill: Literal["none", "x", "y", "both"] | None = None,
    expand: bool | None = None,
    anchor: Literal["nw", "n", "ne", "w", "center", "e", "sw", "s", "se"] | None = None,
    padx: int | tuple[int, int] | None = None,
    pady: int | tuple[int, int] | None = None,
    ipadx: int | None = None,
    ipady: int | None = None,
) -> None:
    """Type-safe wrapper for widget.pack() that accepts keyword arguments.

    This function ensures pyright strict mode passes by using proper keyword-only
    arguments instead of **kwargs, avoiding reportArgumentType errors.

    Args:
        widget: The Tkinter widget to pack.
        side: Which side of the parent to pack against.
        fill: How to fill the allocated space.
        expand: Whether to expand the widget to fill available space.
        anchor: Where to position the widget within its allocated space.
        padx: External padding in the x direction (int or tuple of (left, right)).
        pady: External padding in the y direction (int or tuple of (top, bottom)).
        ipadx: Internal padding in the x direction.
        ipady: Internal padding in the y direction.
    """
    opts: dict[str, Any] = {}
    if side is not None:
        opts["side"] = side
    if fill is not None:
        opts["fill"] = fill
    if expand is not None:
        opts["expand"] = expand
    if anchor is not None:
        opts["anchor"] = anchor
    if padx is not None:
        opts["padx"] = padx
    if pady is not None:
        opts["pady"] = pady
    if ipadx is not None:
        opts["ipadx"] = ipadx
    if ipady is not None:
        opts["ipady"] = ipady

    widget.pack(**opts)


def grid_widget(
    widget: Any,
    *,
    row: int | None = None,
    column: int | None = None,
    rowspan: int | None = None,
    columnspan: int | None = None,
    sticky: str | None = None,
    padx: int | tuple[int, int] | None = None,
    pady: int | tuple[int, int] | None = None,
    ipadx: int | None = None,
    ipady: int | None = None,
) -> None:
    """Type-safe wrapper for widget.grid() that accepts keyword arguments.

    Args:
        widget: The Tkinter widget to grid.
        row: The row position.
        column: The column position.
        rowspan: Number of rows to span.
        columnspan: Number of columns to span.
        sticky: Sticky directions (n, s, e, w, or combinations).
        padx: External padding in the x direction.
        pady: External padding in the y direction.
        ipadx: Internal padding in the x direction.
        ipady: Internal padding in the y direction.
    """
    opts: dict[str, Any] = {}
    if row is not None:
        opts["row"] = row
    if column is not None:
        opts["column"] = column
    if rowspan is not None:
        opts["rowspan"] = rowspan
    if columnspan is not None:
        opts["columnspan"] = columnspan
    if sticky is not None:
        opts["sticky"] = sticky
    if padx is not None:
        opts["padx"] = padx
    if pady is not None:
        opts["pady"] = pady
    if ipadx is not None:
        opts["ipadx"] = ipadx
    if ipady is not None:
        opts["ipady"] = ipady

    widget.grid(**opts)


__all__ = [
    "ListboxProtocol",
    "TextProtocol",
    "EntryProtocol",
    "PackOptions",
    "pack_widget",
    "grid_widget",
]
