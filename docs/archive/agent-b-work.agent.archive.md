# Agent B: Tab Refactoring (DataSession Integration)

**Phase:** 7.1 (Refactor Tabs to Use DataSession)  
**Branch:** `refactor/tab-session-opt-in`  
**Estimated Effort:** Medium-Large (2-3 days)  
**Status:** 🟡 Waiting for Agent A  
**Dependencies:** Agent A complete (requires stable `DataSession` API)

---

## Mission

Refactor GUI tabs (`MergeTab`, `ConvertTab`, `ProbeTab`) to optionally use a shared `DataSession` instance, eliminating redundant file parsing while preserving backward compatibility for tests.

---

## Core Working Instructions

**MUST READ before starting work:**

1. **[code-change.instructions.md](../.github/code-change.instructions.md)** - Policy for every code change
2. **[unit-test-policy.md](unit-test-policy.md)** - Standards for testing
3. **[developer-tooling.md](developer-tooling.md)** - Required workflow commands
4. **[code-remediation-phase-5-12.md](code-remediation-phase-5-12.md)** - Full roadmap context
5. **[agent-a-work.agent.md](agent-a-work.agent.md)** - Agent A's API contracts (your dependency)

**Required workflow after EVERY change:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest`

If any step fails, fix it before proceeding.

---

## Prerequisites (Agent A Deliverables)

**Before starting, verify Agent A completed:**

- [ ] `DataSession` class exists in `quicken_helper/controllers/data_session.py`
- [ ] `DataSession.load_qif(path, encoding="utf-8") -> list[ITransaction]` signature exists
- [ ] `DataSession.load_excel(path) -> list[ExcelTransaction]` signature exists
- [ ] `DataSession` has attributes: `qif_path`, `qif_txns`, `excel_path`, `excel_txns`
- [ ] Agent A's branch merged to master (or you've rebased on their branch)

**If Agent A not complete:** Wait or coordinate directly.

---

## Phase 7.1: Refactor Tabs to Use DataSession (Opt-In)

### Objective
Allow tabs to optionally share a `DataSession` for file loading, while maintaining backward compatibility for tests that don't provide a session.

### Overall Strategy

**"Opt-in" pattern:**
- Tabs accept `session: DataSession | None = None` in constructor
- When `session` is provided AND data already loaded → reuse cached data
- When `session` is `None` OR data not loaded → fall back to direct parsing (existing behavior)
- Tests continue to work by passing `session=None` (or omitting it)

---

## Task 7.1.1: Update MergeTab Constructor

**File:** `quicken_helper/gui_viewers/merge_tab.py`

**Current signature (approximately line 44):**
```python
def __init__(
    self, master: tk.Misc, mb: MessageBoxAPI, session: DataSession | None = None
):
```

**Verify or add:**
1. Constructor already accepts `session: DataSession | None = None` ✅ (appears to be there)
2. Store as instance variable: `self._session = session`
3. Ensure type annotation is correct

**Action:** Read file and verify current state. If missing, add the session parameter and storage.

### Task 7.1.2: Refactor MergeTab QIF Loading

**File:** `quicken_helper/gui_viewers/merge_tab.py`

**Target method:** `_load_qif()` (or wherever QIF loading happens)

**Current pattern (search for):**
```python
# Likely pattern:
with open(qif_path, "r", encoding=encoding) as f:
    text = f.read()
txns = load_transactions_protocol(text)  # or similar
```

**New pattern:**
```python
def _load_qif(self, path: Path, encoding: str = "utf-8") -> list[ITransaction]:
    """Load QIF transactions, using session cache if available."""
    if self._session is not None:
        # Try to reuse cached data
        if self._session.qif_path == path and self._session.qif_txns:
            log.debug("Reusing cached QIF from session: %s", path)
            return self._session.qif_txns
        # Load via session (which caches)
        log.debug("Loading QIF via session: %s", path)
        return self._session.load_qif(path, encoding=encoding)
    
    # Fallback: direct loading (for tests or when no session)
    log.debug("Loading QIF directly (no session): %s", path)
    return list(load_transactions_protocol(path, encoding=encoding))
```

**Invariants:**
- Return type is always `list[ITransaction]`
- Behavior identical when `session=None`
- No UI changes (transparent to user)

### Task 7.1.3: Refactor MergeTab Excel Loading

**File:** `quicken_helper/gui_viewers/merge_tab.py`

**Target method:** `_load_excel()` (or wherever Excel loading happens)

**Current pattern (search for):**
```python
# Likely pattern:
rows = mex.load_excel_rows(excel_path)
groups = mex.group_excel_rows(rows)
txns = [map_group_to_excel_txn(g) for g in groups]
```

**New pattern:**
```python
def _load_excel(self, path: Path) -> list[ExcelTransaction]:
    """Load Excel transactions, using session cache if available."""
    if self._session is not None:
        # Try to reuse cached data
        if self._session.excel_path == path and self._session.excel_txns:
            log.debug("Reusing cached Excel from session: %s", path)
            return self._session.excel_txns
        # Load via session (which caches)
        log.debug("Loading Excel via session: %s", path)
        return self._session.load_excel(path)
    
    # Fallback: direct loading (for tests or when no session)
    log.debug("Loading Excel directly (no session): %s", path)
    rows = mex.load_excel_rows(path)
    groups = mex.group_excel_rows(rows)
    return [map_group_to_excel_txn(g) for g in groups]
```

**Invariants:**
- Return type is always `list[ExcelTransaction]`
- Behavior identical when `session=None`
- No UI changes

---

## Task 7.1.4: Update ConvertTab Constructor

**File:** `quicken_helper/gui_viewers/convert_tab.py`

**Current signature (approximately line 49):**
```python
class ConvertTab(ttk.Frame):
    def __init__(self, parent: tk.Misc, mb: MessageBoxProtocol):
```

**New signature:**
```python
class ConvertTab(ttk.Frame):
    def __init__(
        self, 
        parent: tk.Misc, 
        mb: MessageBoxProtocol,
        session: DataSession | None = None
    ):
        super().__init__(parent)
        self._mb = mb
        self._session = session
        # ... rest of init
```

**Import addition:**
```python
from quicken_helper.controllers.data_session import DataSession
```

### Task 7.1.5: Refactor ConvertTab QIF Loading

**File:** `quicken_helper/gui_viewers/convert_tab.py`

**Target method:** `run()` or wherever QIF parsing happens

**Current pattern (search for):**
```python
# Likely in run() method:
with open(in_path, "r", encoding=encoding) as f:
    text = f.read()
txns = quicken_helper.controllers.qif_loader.load_transactions_protocol(text)
```

**New pattern:**
```python
def _load_qif_transactions(
    self, path: Path, encoding: str = "utf-8"
) -> list[ITransaction]:
    """Load QIF transactions, using session cache if available."""
    if self._session is not None:
        if self._session.qif_path == path and self._session.qif_txns:
            log.debug("Reusing cached QIF from session: %s", path)
            return self._session.qif_txns
        log.debug("Loading QIF via session: %s", path)
        return self._session.load_qif(path, encoding=encoding)
    
    # Fallback: direct loading
    log.debug("Loading QIF directly (no session): %s", path)
    return list(
        quicken_helper.controllers.qif_loader.load_transactions_protocol(
            path, encoding=encoding
        )
    )

# Then in run() method, replace direct parsing with:
txns = self._load_qif_transactions(in_path, encoding=encoding)
```

**Note:** ConvertTab only needs QIF loading (no Excel).

---

## Task 7.1.6: Update ProbeTab Constructor

**File:** `quicken_helper/gui_viewers/probe_tab.py`

**Current signature (search for class definition):**
```python
class ProbeTab(ttk.Frame):
    def __init__(self, parent: tk.Misc):
```

**New signature:**
```python
class ProbeTab(ttk.Frame):
    def __init__(
        self, 
        parent: tk.Misc,
        session: DataSession | None = None
    ):
        super().__init__(parent)
        self._session = session
        # ... rest of init
```

**Import addition:**
```python
from quicken_helper.controllers.data_session import DataSession
```

### Task 7.1.7: Refactor ProbeTab File Loading

**File:** `quicken_helper/gui_viewers/probe_tab.py`

**Strategy:** ProbeTab does inspection/probing, not long-lived data storage. Session integration may be minimal.

**Options:**
1. If ProbeTab loads QIF/QDX for inspection, optionally use `session.load_qif()` to populate cache
2. If ProbeTab is read-only inspection, session integration may not be necessary

**Action:** 
- Review ProbeTab loading logic
- If it loads QIF, apply same pattern as ConvertTab
- If it's purely diagnostic, document why session not used and mark task complete

**Document decision in PR description.**

---

## Task 7.1.8: Wire DataSession in App

**File:** `quicken_helper/gui_viewers/app.py`

**Current pattern (approximately line 20-40):**
```python
class App:
    def __init__(self, master: tk.Tk):
        self.root = master
        # ...
        notebook = ttk.Notebook(master)
        
        # Tabs created without session
        merge_tab = MergeTab(notebook, mb=...)
        convert_tab = ConvertTab(notebook, mb=...)
        probe_tab = ProbeTab(notebook)
```

**New pattern:**
```python
from quicken_helper.controllers.data_session import DataSession

class App:
    def __init__(self, master: tk.Tk):
        self.root = master
        
        # Create shared session
        self._session = DataSession()
        
        # ...
        notebook = ttk.Notebook(master)
        
        # Pass session to all tabs
        merge_tab = MergeTab(notebook, mb=..., session=self._session)
        convert_tab = ConvertTab(notebook, mb=..., session=self._session)
        probe_tab = ProbeTab(notebook, session=self._session)
```

**Invariants:**
- All tabs receive the same `DataSession` instance
- Session lives for app lifetime (no premature cleanup)
- No other app logic changes

---

## API Contracts (Promises to Other Agents)

### Agent B commits to:

**1. Backward-compatible tab constructors:**
```python
# All tabs accept optional session
MergeTab(master, mb, session=None)
ConvertTab(parent, mb, session=None)
ProbeTab(parent, session=None)
```

**2. Session usage pattern:**
- When `session` provided → use `session.load_qif()` / `session.load_excel()`
- When `session=None` → fall back to direct loading
- Behavior identical in both cases

**3. No breaking changes:**
- Existing tests pass without modification (they pass `session=None` implicitly)
- App now wires session, but tabs don't require it

### Agent B consumes:
- Agent A's `DataSession` API (completed prerequisite)

### Agent C works independently:
- No direct interaction with Agent B's work
- May eventually integrate with updated tabs, but not initially

---

## Testing Strategy

### Existing Tests Must Stay Green

**Without modification:**
- `tests/gui_viewers/test_merge_tab.py` - instantiate with `session=None`
- `tests/gui_viewers/test_convert_tab.py` - instantiate with `session=None`
- `tests/gui_viewers/test_app.py` - will now pass session, but tabs handle it gracefully

**Verification:**
```powershell
poetry run pytest tests/gui_viewers/ -v
```

### New Tests (Optional but Recommended)

**Test session reuse behavior:**

```python
# tests/gui_viewers/test_merge_tab_session.py
from pathlib import Path
from quicken_helper.controllers.data_session import DataSession
from quicken_helper.gui_viewers.merge_tab import MergeTab

def test_merge_tab_reuses_session_qif_cache(tmp_path, monkeypatch):
    """
    Verify MergeTab reuses QIF transactions from DataSession cache.
    
    Follows unit-test-policy.md: isolated, deterministic.
    """
    # Arrange
    qif_path = tmp_path / "test.qif"
    qif_path.write_text("!Type:Bank\n^")
    
    session = DataSession()
    session.load_qif(qif_path)  # Pre-load
    
    root = tk.Tk()
    mb = _MockMessageBox()
    tab = MergeTab(root, mb, session=session)
    
    # Spy to ensure load_qif not called again
    load_count = 0
    original_load = session.load_qif
    def spy_load(*args, **kwargs):
        nonlocal load_count
        load_count += 1
        return original_load(*args, **kwargs)
    monkeypatch.setattr(session, "load_qif", spy_load)
    
    # Act
    tab._load_qif(qif_path)  # Should use cache
    
    # Assert
    assert load_count == 0, "Should reuse cache, not reload"
    root.destroy()
```

**Similar test for Excel, ConvertTab, etc.**

---

## Files Modified Summary

### Primary modifications:
1. `quicken_helper/gui_viewers/merge_tab.py` - add session param, refactor loading
2. `quicken_helper/gui_viewers/convert_tab.py` - add session param, refactor loading
3. `quicken_helper/gui_viewers/probe_tab.py` - add session param (minimal changes)
4. `quicken_helper/gui_viewers/app.py` - create and wire DataSession

### Files to read (context):
- `quicken_helper/controllers/data_session.py` (Agent A's deliverable)
- `quicken_helper/controllers/qif_loader.py` (loading patterns)
- `quicken_helper/controllers/match_excel.py` (Excel loading patterns)
- `tests/gui_viewers/*.py` (existing test patterns)

---

## Completion Criteria

**Before opening PR:**

1. **All tools pass:**
   - [ ] `poetry run black .` - no changes needed
   - [ ] `poetry run ruff check` - zero errors
   - [ ] `poetry run pyright` - zero errors in modified files
   - [ ] `poetry run pytest` - all tests pass

2. **Code quality:**
   - [ ] All tab constructors accept `session: DataSession | None = None`
   - [ ] Loading methods check `self._session` before falling back
   - [ ] Return types consistent (`list[ITransaction]`, `list[ExcelTransaction]`)
   - [ ] Log calls added per Agent A's pattern

3. **Backward compatibility:**
   - [ ] All existing GUI tests pass without modification
   - [ ] Tabs work correctly when `session=None`
   - [ ] Tabs work correctly when session provided

4. **Integration:**
   - [ ] `app.py` creates single `DataSession` and passes to all tabs
   - [ ] Manual smoke test: launch app, load files in multiple tabs, verify caching

5. **Documentation:**
   - [ ] Update this file with "Status: ✅ Complete"
   - [ ] Document any deviations in PR description
   - [ ] Note ProbeTab decision (session used or not)

---

## Merge Strategy

**Target branch:** `master` (or current active development branch)

**Merge order:** Second (after Agent A, before Agent D)

**Why:** Establishes tab→session integration before app shim removal (Phase 8).

**Pre-merge checklist:**
- [ ] Agent A's branch merged
- [ ] All completion criteria met
- [ ] PR opened with clear description
- [ ] CI passes
- [ ] No merge conflicts with master

---

## Manual Verification Steps

**After implementation, test manually:**

1. **Launch GUI:**
   ```powershell
   poetry run python -m quicken_helper.gui_viewers.app
   ```

2. **ConvertTab:**
   - Load a QIF file
   - Verify console shows "Loading QIF via session: ..."
   - Switch to MergeTab, load same QIF
   - Verify console shows "Reusing cached QIF from session: ..."

3. **MergeTab:**
   - Load QIF + Excel
   - Verify both show "Loading via session" or "Reusing cached"
   - Perform match operation
   - Verify no crashes, data displays correctly

4. **ProbeTab:**
   - Load a QIF/QDX file
   - Verify inspection works as before

5. **Edge cases:**
   - Load file A, then file B (different paths) → should reload, not cache
   - Load same file twice → should reuse cache second time

---

## Communication & Handoff

**When Agent B completes:**

1. Update `docs/agent-work-allocation.md` status to "✅ Complete"
2. Post commit SHA where tab integration is stable
3. Notify Agent D they can begin Phase 8 (app shim removal)
4. Document any integration issues discovered

**If blocked:**
- Check Agent A's deliverables meet contract
- Coordinate with Agent A if `DataSession` API needs adjustment
- Document any blockers in `docs/agent-work-allocation.md`

---

## Quick Reference Commands

```powershell
# Start work (after Agent A merged)
git checkout master
git pull
git checkout -b refactor/tab-session-opt-in

# Run full workflow (after each change)
poetry run black .
poetry run ruff check
poetry run pyright
poetry run pytest

# Run targeted tests (faster iteration)
poetry run pytest tests/gui_viewers/ -v
poetry run pytest tests/gui_viewers/test_merge_tab.py -v

# Type-check specific file
poetry run pyright quicken_helper/gui_viewers/merge_tab.py

# Launch GUI for manual verification
poetry run python -m quicken_helper.gui_viewers.app

# Check for session usage (search)
rg "self\._session" quicken_helper/gui_viewers/
```

---

## Status Tracking

**Current status:** 🟡 Waiting for Agent A  
**Agent A complete:** [ ]  
**Branch created:** [ ]  
**MergeTab refactored:** [ ]  
**ConvertTab refactored:** [ ]  
**ProbeTab refactored:** [ ]  
**App wired:** [ ]  
**Manual verification:** [ ]  
**PR opened:** [ ]  
**PR merged:** [ ]  

**Last updated:** 2025-01-19  
**Agent assigned:** _[Your Name/ID]_
