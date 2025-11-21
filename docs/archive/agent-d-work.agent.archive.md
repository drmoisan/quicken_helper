# Agent D: Cleanup & Polish

**Phases:** 8 (App Shim Removal), 10 (I/O Centralization), 11 (Error Reporting)  
**Branch:** `refactor/app-cleanup`  
**Estimated Effort:** Medium (2-3 days)  
**Status:** ⏸️ Blocked (waiting for A, B, C)  
**Dependencies:** Agents A, B, C must complete and merge first

---

## Mission

Clean up app architecture by removing shims, centralizing I/O operations, and adding rich error reporting. This is the final cleanup phase that makes the codebase maintainable and follows "load once, work in memory, write once" principles.

---

## Core Working Instructions

**MUST READ before starting work:**

1. **[code-change.instructions.md](../.github/code-change.instructions.md)** - Policy for every code change
2. **[unit-test-policy.md](unit-test-policy.md)** - Standards for testing
3. **[developer-tooling.md](developer-tooling.md)** - Required workflow commands
4. **[code-remediation-phase-5-12.md](code-remediation-phase-5-12.md)** - Full roadmap context (Phases 8, 10, 11)
5. **[agent-a-work.agent.md](agent-a-work.agent.md)** - Agent A's deliverables
6. **[agent-b-work.agent.md](agent-b-work.agent.md)** - Agent B's deliverables
7. **[agent-c-work.agent.md](agent-c-work.agent.md)** - Agent C's deliverables

**Required workflow after EVERY change:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest`

If any step fails, fix it before proceeding.

---

## Prerequisites (Other Agents' Deliverables)

**Before starting, verify these are merged to master:**

### Agent A (Foundation):
- [ ] `DataSession` exists and is stable
- [ ] Logging added to GUI tabs and controllers
- [ ] All Agent A tests passing

### Agent B (Tab Refactoring):
- [ ] Tabs accept and use `DataSession` optionally
- [ ] App wires `DataSession` to all tabs
- [ ] All tab tests passing

### Agent C (Match Pipeline):
- [ ] `MatchSession` has clean protocol API
- [ ] `build_matched_only_txns()` exists
- [ ] `run_excel_qif_merge()` refactored
- [ ] QIF writer accepts protocols
- [ ] All match tests passing

**Verification:**
```powershell
git checkout master
git pull
poetry run pytest  # Should be all green from A, B, C work
```

---

## Phase 8: App Shim Removal + Test Migration

### Objective
Make `App` a pure UI wiring class with no business logic. Move all shims to appropriate tabs.

---

## Task 8.1: Identify App Shims

**File:** `quicken_helper/gui_viewers/app.py`

**Read file and identify shims:**
```powershell
# Search for app-level attributes/methods that shouldn't be there
rg "def _" quicken_helper/gui_viewers/app.py
rg "self\.(in_path|out_path|emit_var)" quicken_helper/gui_viewers/app.py
```

**Common shims to look for:**
- `self.in_path` / `self.out_path` - file paths
- `self.emit_var` - emit mode selection
- `_update_output_extension()` - path/extension logic
- `_parse_payee_filters()` - filter parsing
- `_run()` - actual conversion logic
- `_m_normalize_categories()` - category normalization delegation

**Create removal plan:**
- [ ] List all shim attributes
- [ ] List all shim methods
- [ ] Identify where each belongs (which tab)
- [ ] List all tests that reference shims

---

## Task 8.1.1: Move Path/Extension Logic to ConvertTab

**Target shims in app.py:**
- `self.in_path`, `self.out_path`
- `_update_output_extension()`

**File to modify:** `quicken_helper/gui_viewers/convert_tab.py`

**Move logic into ConvertTab:**
```python
class ConvertTab(ttk.Frame):
    def __init__(self, parent: tk.Misc, mb: MessageBoxProtocol, session: DataSession | None = None):
        super().__init__(parent)
        self._mb = mb
        self._session = session
        
        # Tab-local path storage
        self._in_path: Path | None = None
        self._out_path: Path | None = None
        
        # ... rest of init
    
    def _update_output_extension(self, emit_mode: str) -> None:
        """Update output path extension based on emit mode."""
        if not self._out_path or self._out_path == Path(""):
            # Blank output → derive from input
            if self._in_path:
                self._out_path = self._in_path.with_suffix(
                    ".csv" if emit_mode == "csv" else ".qif"
                )
        else:
            # Existing output → switch extension
            new_suffix = ".csv" if emit_mode == "csv" else ".qif"
            self._out_path = self._out_path.with_suffix(new_suffix)
```

**Remove from app.py:**
- Delete `_update_output_extension()` method
- Delete `in_path`, `out_path` attributes
- Remove any calls to these from app

---

## Task 8.1.2: Move Payee Filter Parsing to ConvertTab

**Target shim in app.py:**
- `_parse_payee_filters()`

**File to modify:** `quicken_helper/gui_viewers/convert_tab.py`

**Move logic into ConvertTab:**
```python
class ConvertTab(ttk.Frame):
    # ...
    
    def _parse_payee_filters(self, text: str) -> list[str]:
        """
        Parse payee filter text into list of filter strings.
        
        Supports:
        - Newline-separated filters
        - Comma-separated filters
        - Mixed formats
        
        Returns:
            List of non-empty filter strings
        """
        # Split by newlines first
        lines = text.strip().split("\n")
        filters = []
        for line in lines:
            # Split each line by commas
            parts = line.split(",")
            for part in parts:
                cleaned = part.strip()
                if cleaned:
                    filters.append(cleaned)
        return filters
```

**Remove from app.py:**
- Delete `_parse_payee_filters()` method
- Remove any calls from app

---

## Task 8.1.3: Remove Normalize Categories Delegation

**Target shim in app.py:**
- `_m_normalize_categories()` (delegates to MergeTab)

**Action:**
- This is already handled by MergeTab directly
- Simply remove the app-level method
- Update any menu/button bindings to call MergeTab method directly

**Verification:**
- Check `tests/gui_viewers/test_app.py` for test like `test_m_normalize_categories_delegates_to_merge_tab`
- This test will be removed in Task 8.2.3

---

## Task 8.1.4: Simplify App.__init__

**File:** `quicken_helper/gui_viewers/app.py`

**After removing all shims, App should look like:**
```python
class App:
    """Main application window that wires tabs together."""
    
    def __init__(self, master: tk.Tk):
        self.root = master
        master.title("Quicken Helper")
        
        # Create shared session
        self._session = DataSession()
        
        # Create message box API
        mb = MessageBoxAPI()
        
        # Create notebook
        notebook = ttk.Notebook(master)
        notebook.pack(fill="both", expand=True)
        
        # Create tabs (order: Merge, Convert, Probe)
        self._merge_tab = MergeTab(notebook, mb, session=self._session)
        self._convert_tab = ConvertTab(notebook, mb, session=self._session)
        self._probe_tab = ProbeTab(notebook, session=self._session)
        
        # Add tabs to notebook
        notebook.add(self._merge_tab, text="Merge")
        notebook.add(self._convert_tab, text="Convert")
        notebook.add(self._probe_tab, text="Probe")
        
        # Optional: Set up menu bar, if needed
        self._setup_menu()
    
    def _setup_menu(self) -> None:
        """Set up application menu bar."""
        # Menu items should delegate directly to tabs
        # Example: File → Normalize Categories → calls merge_tab method
        pass
```

**Invariants:**
- App only creates and wires components
- No business logic in App
- No file paths stored in App
- No emit mode stored in App

---

## Task 8.2: Migrate and Trim test_app.py

### Task 8.2.1: Keep and Trim Initialization Test

**File:** `tests/gui_viewers/test_app.py`

**Find test like:** `test_app_init_wires_tabs_and_shims`

**Rename and trim to:**
```python
def test_app_init_builds_tabs():
    """
    Verify App creates root window, notebook, and three tabs.
    
    Tests UI wiring only, not business logic. Follows unit-test-policy.md.
    """
    # Arrange
    root = tk.Tk()
    
    # Act
    app = App(root)
    
    # Assert
    assert app.root is root, "Should store root reference"
    assert hasattr(app, "_session"), "Should create DataSession"
    assert isinstance(app._session, DataSession), "Session should be DataSession instance"
    assert hasattr(app, "_merge_tab"), "Should create MergeTab"
    assert hasattr(app, "_convert_tab"), "Should create ConvertTab"
    assert hasattr(app, "_probe_tab"), "Should create ProbeTab"
    
    # Verify notebook has 3 tabs
    notebook = _find_notebook_widget(root)
    assert notebook is not None, "Should have notebook widget"
    assert len(notebook.tabs()) == 3, "Should have 3 tabs"
    
    # Cleanup
    root.destroy()
```

**Remove assertions about:**
- `app.in_path`
- `app.out_path`
- `app.emit_var`
- Any shim methods

### Task 8.2.2: Migrate Tests to test_convert_tab.py

**Tests to migrate from test_app.py to test_convert_tab.py:**

1. `test_update_output_extension_blank_out_uses_in_path`
2. `test_update_output_extension_switches_extension`
3. `test_parse_payee_filters_parses_lines_and_commas`
4. `test_run_missing_input_shows_error`
5. `test_run_missing_output_shows_error`
6. `test_run_decline_overwrite_does_not_write`
7. `test_run_writes_csv_windows_profile`

**For each test:**
- Copy to `test_convert_tab.py`
- Rewrite to instantiate `ConvertTab` directly (not `App`)
- Update to use test doubles (mock Tk root, mock messagebox)
- Ensure follows unit-test-policy.md (docstring, AAA pattern)

**Example migration:**
```python
# Original in test_app.py:
def test_update_output_extension_blank_out_uses_in_path():
    app = App(tk.Tk())
    app.in_path = Path("input.qif")
    app.out_path = Path("")
    app._update_output_extension("csv")
    assert app.out_path == Path("input.csv")

# Migrated to test_convert_tab.py:
def test_update_output_extension_blank_out_uses_in_path():
    """
    Verify blank output path derives from input path with correct extension.
    
    Tests path logic in ConvertTab. Follows unit-test-policy.md.
    """
    # Arrange
    root = tk.Tk()
    mb = _MockMessageBox()
    tab = ConvertTab(root, mb)
    tab._in_path = Path("input.qif")
    tab._out_path = Path("")
    
    # Act
    tab._update_output_extension("csv")
    
    # Assert
    assert tab._out_path == Path("input.csv"), "Should derive CSV path from input"
    
    # Cleanup
    root.destroy()
```

### Task 8.2.3: Remove Redundant Tests

**Tests to delete entirely from test_app.py:**

1. `test_m_normalize_categories_delegates_to_merge_tab`
   - Reason: Covered by MergeTab tests directly
   
2. Any QIF write tests that duplicate `test_qif_writer.py` or `test_merge_tab.py`

**Verification:**
```powershell
poetry run pytest tests/gui_viewers/test_app.py -v
poetry run pytest tests/gui_viewers/test_convert_tab.py -v
# Both should pass; app tests should be minimal
```

---

## Phase 10: Centralize I/O Operations

### Objective
Create dedicated I/O service that centralizes write operations, making tabs UI-only.

---

## Task 10.1: Create io_service Module

**New file:** `quicken_helper/controllers/io_service.py`

**Content:**
```python
"""
Centralized I/O operations for writing QIF and CSV files.

Separates I/O concerns from business logic and UI.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from quicken_helper.data_model.interfaces import ITransaction

log = logging.getLogger(__name__)


def write_qif(
    transactions: Sequence[ITransaction],
    path: Path,
    *,
    encoding: str = "utf-8",
) -> None:
    """
    Write transactions to QIF file.
    
    Args:
        transactions: Transactions to write
        path: Output file path
        encoding: Text encoding (default UTF-8)
        
    Raises:
        IOError: If file cannot be written
        TypeError: If transactions don't implement ITransaction
    """
    log.info("Writing %d transactions to QIF: %s", len(transactions), path)
    
    # Delegate to existing QIF writer
    from quicken_helper.legacy.qif_writer import write_qif as legacy_write_qif
    
    try:
        legacy_write_qif(list(transactions), path, encoding=encoding)
        log.debug("Successfully wrote QIF: %s", path)
    except Exception as e:
        log.exception("Failed to write QIF: %s", path)
        raise IOError(f"Failed to write QIF file: {e}") from e


def write_csv(
    transactions: Sequence[ITransaction],
    path: Path,
    profile: str = "quicken_windows",
    *,
    encoding: str = "utf-8",
) -> None:
    """
    Write transactions to CSV file using specified profile.
    
    Args:
        transactions: Transactions to write
        path: Output file path
        profile: CSV profile name ("quicken_windows" or "quicken_mac")
        encoding: Text encoding (default UTF-8)
        
    Raises:
        IOError: If file cannot be written
        ValueError: If profile unknown
    """
    log.info(
        "Writing %d transactions to CSV (%s): %s",
        len(transactions),
        profile,
        path,
    )
    
    # Delegate to CSV profile writers
    from quicken_helper.gui_viewers.csv_profiles import (
        write_csv_quicken_mac,
        write_csv_quicken_windows,
    )
    
    try:
        if profile == "quicken_windows":
            write_csv_quicken_windows(list(transactions), path, encoding=encoding)
        elif profile == "quicken_mac":
            write_csv_quicken_mac(list(transactions), path, encoding=encoding)
        else:
            raise ValueError(f"Unknown CSV profile: {profile}")
        
        log.debug("Successfully wrote CSV: %s", path)
    except Exception as e:
        log.exception("Failed to write CSV: %s", path)
        raise IOError(f"Failed to write CSV file: {e}") from e
```

### Task 10.2: Update Tabs to Use io_service

**Files to modify:**
- `quicken_helper/gui_viewers/convert_tab.py`
- `quicken_helper/gui_viewers/merge_tab.py`

**Pattern in ConvertTab:**
```python
# Old:
from quicken_helper.legacy import qif_writer
qif_writer.write_qif(txns, out_path)

# New:
from quicken_helper.controllers.io_service import write_qif, write_csv

# In run() method:
if emit_mode == "qif":
    write_qif(txns, out_path, encoding=encoding)
elif emit_mode == "csv":
    write_csv(txns, out_path, profile=profile, encoding=encoding)
```

**Pattern in MergeTab:**
```python
# Old:
from quicken_helper.legacy import qif_writer
qif_writer.write_qif(txns, out_path)

# New:
from quicken_helper.controllers.io_service import write_qif

# In write method:
write_qif(txns, out_path, encoding=self._encoding)
```

**Invariants:**
- Tabs never open files for writing directly
- All writes go through io_service
- Error handling in io_service, not tabs

---

## Phase 11: Rich Error Reporting

### Objective
Structured error reporting with statistics and diagnostics.

---

## Task 11.1: Add Parse Stats to Controllers

**Files to modify:**
- `quicken_helper/controllers/qif_loader.py`
- `quicken_helper/controllers/match_excel.py`

**Pattern (example for qif_loader):**
```python
from dataclasses import dataclass

@dataclass
class ParseStats:
    """Statistics from file parsing operation."""
    lines_read: int
    transactions_parsed: int
    transactions_skipped: int
    errors: list[str]  # Sample errors (max 3)

def load_transactions_protocol(
    path: Path, *, encoding: str = "utf-8"
) -> tuple[list[ITransaction], ParseStats]:
    """
    Load transactions and return parse statistics.
    
    Returns:
        Tuple of (transactions, stats)
    """
    lines_read = 0
    parsed = 0
    skipped = 0
    errors = []
    
    # ... parsing logic
    
    stats = ParseStats(
        lines_read=lines_read,
        transactions_parsed=parsed,
        transactions_skipped=skipped,
        errors=errors[:3],  # Keep only first 3 errors
    )
    
    return (transactions, stats)
```

**Note:** This changes return signature. Consider:
- Adding new function `load_with_stats()` to avoid breaking existing code
- Or updating all call sites to unpack tuple

### Task 11.2: Surface Stats in GUI

**Files to modify:**
- `quicken_helper/gui_viewers/convert_tab.py`
- `quicken_helper/gui_viewers/merge_tab.py`

**Pattern:**
```python
# After loading:
txns, stats = load_transactions_protocol(path)

# Log stats:
log.info(
    "Parsed %d/%d transactions (%d skipped, %d errors)",
    stats.transactions_parsed,
    stats.lines_read,
    stats.transactions_skipped,
    len(stats.errors),
)

# Optionally show in UI:
if stats.errors:
    error_summary = "\n".join(stats.errors)
    self._mb.showinfo(
        "Parse Warnings",
        f"Parsed {stats.transactions_parsed} transactions\n"
        f"Encountered {len(stats.errors)} errors:\n{error_summary}"
    )
```

**Invariants:**
- Stats logged for diagnostics
- Errors surfaced to user only if significant
- Full logs in log file for detailed troubleshooting

---

## Testing Strategy

### Tests to Update

**Phase 8 (App cleanup):**
- Trim `tests/gui_viewers/test_app.py`
- Migrate tests to `test_convert_tab.py`
- All GUI tests should pass

**Phase 10 (I/O service):**
- Add `tests/controllers/test_io_service.py`
- Test `write_qif()` with protocol objects
- Test `write_csv()` with both profiles
- Test error handling (invalid paths, etc.)

**Phase 11 (Error reporting):**
- Update loader tests to verify stats returned
- Test edge cases (empty files, malformed data)
- Verify log output includes stats

### New Test File: test_io_service.py

```python
# tests/controllers/test_io_service.py
from pathlib import Path
from quicken_helper.controllers.io_service import write_qif, write_csv

def test_write_qif_creates_valid_file(tmp_path):
    """
    Verify write_qif creates valid QIF file from transactions.
    
    Tests I/O service write operation. Follows unit-test-policy.md.
    """
    # Arrange
    txn = _make_transaction(date="2025-01-01", amount=100)
    out_file = tmp_path / "output.qif"
    
    # Act
    write_qif([txn], out_file)
    
    # Assert
    assert out_file.exists(), "Should create output file"
    content = out_file.read_text()
    assert "!Type:Bank" in content
    assert "^" in content


def test_write_csv_windows_profile(tmp_path):
    """Verify write_csv creates valid CSV with Windows profile."""
    # Arrange
    txn = _make_transaction(date="2025-01-01", amount=100, payee="Test")
    out_file = tmp_path / "output.csv"
    
    # Act
    write_csv([txn], out_file, profile="quicken_windows")
    
    # Assert
    assert out_file.exists()
    content = out_file.read_text()
    assert "Date" in content  # Header
    assert "2025-01-01" in content or "01/01/2025" in content


def test_write_csv_unknown_profile_raises(tmp_path):
    """Verify write_csv raises ValueError for unknown profile."""
    # Arrange
    txn = _make_transaction(date="2025-01-01", amount=100)
    out_file = tmp_path / "output.csv"
    
    # Act & Assert
    with pytest.raises(ValueError, match="Unknown CSV profile"):
        write_csv([txn], out_file, profile="unknown")
```

---

## Completion Criteria

**Before opening PR:**

1. **All tools pass:**
   - [ ] `poetry run black .` - no changes needed
   - [ ] `poetry run ruff check` - zero errors
   - [ ] `poetry run pyright` - zero errors
   - [ ] `poetry run pytest` - all tests pass

2. **Phase 8 (App cleanup):**
   - [ ] All shims removed from app.py
   - [ ] Logic moved to appropriate tabs
   - [ ] test_app.py trimmed (minimal wiring tests only)
   - [ ] Tests migrated to test_convert_tab.py
   - [ ] All GUI tests pass

3. **Phase 10 (I/O centralization):**
   - [ ] `io_service.py` created with `write_qif()` and `write_csv()`
   - [ ] Tabs use io_service (no direct file writes)
   - [ ] test_io_service.py created with comprehensive tests
   - [ ] All write operations tested

4. **Phase 11 (Error reporting):**
   - [ ] ParseStats or equivalent added to loaders
   - [ ] Stats logged in controllers
   - [ ] Stats optionally surfaced in GUI
   - [ ] Error handling comprehensive

5. **Documentation:**
   - [ ] Update this file with "Status: ✅ Complete"
   - [ ] Document any deviations in PR
   - [ ] Update README if needed

---

## Merge Strategy

**Target branch:** `master`

**Merge order:** Last (after A, B, C all merged)

**Why:** Cleanup phase that depends on all prior refactoring being complete.

**Pre-merge checklist:**
- [ ] Agents A, B, C all merged
- [ ] All completion criteria met
- [ ] PR opened with clear description
- [ ] CI passes
- [ ] Code review complete

---

## Communication & Handoff

**When Agent D completes:**

1. Update `docs/agent-work-allocation.md` status to "✅ Complete"
2. Phases 5-11 of roadmap complete! 🎉
3. Document lessons learned
4. Propose next steps (Phase 12 or other improvements)

**If blocked:**
- Ensure A, B, C merged first
- Coordinate if API changes needed
- Document blockers in tracking file

---

## Quick Reference Commands

```powershell
# Start work (after A, B, C merged)
git checkout master
git pull
git checkout -b refactor/app-cleanup

# Run full workflow
poetry run black .
poetry run ruff check
poetry run pyright
poetry run pytest

# Run targeted tests
poetry run pytest tests/gui_viewers/ -v
poetry run pytest tests/controllers/test_io_service.py -v

# Search for shims
rg "def _" quicken_helper/gui_viewers/app.py
rg "self\.(in_path|out_path|emit_var)" quicken_helper/gui_viewers/

# Launch GUI for verification
poetry run python -m quicken_helper.gui_viewers.app
```

---

## Status Tracking

**Current status:** ⏸️ Blocked (waiting for A, B, C)  
**Agent A merged:** [ ]  
**Agent B merged:** [ ]  
**Agent C merged:** [ ]  
**Branch created:** [ ]  
**Phase 8 complete:** [ ]  
**Phase 10 complete:** [ ]  
**Phase 11 complete:** [ ]  
**PR opened:** [ ]  
**PR merged:** [ ]  

**Last updated:** 2025-01-19  
**Agent assigned:** _[Your Name/ID]_
