
# Agent A: Foundation & Infrastructure

**Phases:** 5 (Logging), 6.2 (DataSession Completion)  
**Branch:** `refactor/logging-foundation`  
**Estimated Effort:** Medium (1-2 days)  
**Status:** 🟡 Ready to Start  
**Dependencies:** None (can start immediately)

---

## Mission

Establish logging infrastructure across GUI tabs and controllers, and complete the `DataSession` API so other agents can depend on it. This work is **additive only**—no breaking changes to existing functionality.

---

## Core Working Instructions

**MUST READ before starting work:**

1. **[code-change.instructions.md](../.github/code-change.instructions.md)** - Policy for every code change
2. **[unit-test-policy.md](unit-test-policy.md)** - Standards for testing
3. **[developer-tooling.md](developer-tooling.md)** - Required workflow commands
4. **[code-remediation-phase-5-12.md](code-remediation-phase-5-12.md)** - Full roadmap context

**Required workflow after EVERY change:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest`

If any step fails, fix it before proceeding.

---

## Phase 5: Logging Infrastructure

### Objective
Add consistent, low-risk logging to GUI tabs and controllers without changing behavior.

### 5.1 Add Module-Level Loggers

**Files to modify:**
- `quicken_helper/gui_viewers/convert_tab.py`
- `quicken_helper/gui_viewers/probe_tab.py`
- `quicken_helper/controllers/match_excel.py`
- `quicken_helper/controllers/match_session.py`

**Pattern to apply:**

```python
# At top of each module (after imports)
import logging
log = logging.getLogger(__name__)
```

**Where to add logging calls:**

1. **File path selections:**
   ```python
   log.info("Selected input file: %s", path)
   log.info("Selected output file: %s", path)
   ```

2. **Emit mode/profile selections:**
   ```python
   log.debug("Emit mode: %s", mode)  # "qif", "csv", etc.
   log.debug("CSV profile: %s", profile_name)
   ```

3. **Start/finish of operations:**
   ```python
   log.info("Starting QIF parse: %s", in_path)
   log.debug("Parsed %d transactions from %s", len(txns), in_path)
   log.info("Writing output: %s", out_path)
   ```

4. **Exception paths (before messagebox):**
   ```python
   try:
       # ... operation
   except Exception as e:
       log.exception("Failed to parse QIF file: %s", path)
       messagebox.showerror("Error", f"Failed: {e}")
   ```

**Invariants:**
- ✅ No behavior changes—existing tests must remain green
- ✅ No new `Any` types introduced
- ✅ Log statements must not raise exceptions themselves
- ✅ Use `%s` formatting, not f-strings, for log messages (lazy evaluation)

### Verification Checklist for Phase 5

- [ ] `convert_tab.py` has module-level logger
- [ ] `convert_tab.py` logs: input/output selection, emit mode, parse start/finish, exceptions
- [ ] `probe_tab.py` has module-level logger
- [ ] `probe_tab.py` logs: file selection, probe start/finish, exceptions
- [ ] Verify `merge_tab.py` already has logger (line 32); if missing, add it
- [ ] `match_excel.py` has module-level logger
- [ ] `match_excel.py` logs: Excel load start/finish, group counts, exceptions
- [ ] `match_session.py` has module-level logger
- [ ] `match_session.py` logs: match operations, pair counts, update operations
- [ ] Run `poetry run pytest tests/gui_viewers/` - all green
- [ ] Run `poetry run pytest tests/controllers/` - all green
- [ ] Run `poetry run pyright` - no new errors
- [ ] Manual smoke test: Launch GUI, verify logs appear in console/file

---

## Phase 6.2: DataSession API Completion

### Objective
Ensure `DataSession` loaders return clean, typed transaction lists that other agents can depend on.

### 6.2.1 Verify QIF Loader Returns `list[ITransaction]`

**File:** `quicken_helper/controllers/qif_loader.py`

**Current state check:**
- Read the file and verify `load_transactions_protocol()` signature
- Verify return type is `list[ITransaction]` or compatible iterator

**If changes needed:**
- Ensure function signature is:
  ```python
  def load_transactions_protocol(
      path: Path | str, 
      *, 
      encoding: str = "utf-8"
  ) -> list[ITransaction]:
  ```
- Ensure all return paths yield objects implementing `ITransaction`
- Add type annotations if missing
- Run Pyright to verify

**Verification:**
```python
# This should pass type checking
from quicken_helper.controllers.qif_loader import load_transactions_protocol
from quicken_helper.data_model.interfaces import ITransaction

txns: list[ITransaction] = load_transactions_protocol("test.qif")
```

### 6.2.2 Standardize Excel → Transaction Conversion

**File:** `quicken_helper/controllers/match_excel.py`

**Task:** Create or verify helper function exists

**Target signature:**
```python
def excel_groups_to_txns(groups: list[ExcelTxnGroup]) -> list[ExcelTransaction]:
    """
    Convert Excel transaction groups to ExcelTransaction objects.
    
    Uses existing adapter logic (map_group_to_excel_txn).
    """
    return [map_group_to_excel_txn(g) for g in groups]
```

**Notes:**
- This may already exist implicitly in `DataSession.load_excel()`
- If so, extract it as a standalone function for reusability
- Ensure it's exported from the module

**Verification:**
- Check `DataSession.load_excel()` uses this helper (or equivalent)
- Verify return type matches `list[ExcelTransaction]`
- Run existing tests: `poetry run pytest tests/controllers/test_match_excel.py`

### 6.2.3 Verify DataSession API Stability

**File:** `quicken_helper/controllers/data_session.py`

**Contract verification:**
Confirm the following public API exists and is typed:

```python
@dataclass
class DataSession:
    # Attributes
    qif_path: Path | None
    qif_txns: list[ITransaction]
    excel_path: Path | None
    excel_txns: list[ExcelTransaction]
    
    # Methods
    def load_qif(self, path: Path, *, encoding: str = "utf-8") -> list[ITransaction]:
        """Load QIF and cache transactions. Returns cached if path unchanged."""
        ...
    
    def load_excel(self, path: Path) -> list[ExcelTransaction]:
        """Load Excel and cache transactions. Returns cached if path unchanged."""
        ...
```

**If changes needed:**
- Add missing type annotations
- Ensure methods are idempotent (reload only if path changes)
- Add logging calls as per Phase 5 pattern
- Document caching behavior in docstrings

### Verification Checklist for Phase 6.2

- [ ] `qif_loader.load_transactions_protocol()` returns `list[ITransaction]`
- [ ] `qif_loader.py` passes Pyright with no errors
- [ ] `match_excel.py` has `excel_groups_to_txns()` helper (or equivalent)
- [ ] `match_excel.py` helper is type-clean and tested
- [ ] `DataSession` has all required attributes with correct types
- [ ] `DataSession.load_qif()` has correct signature and returns `list[ITransaction]`
- [ ] `DataSession.load_excel()` has correct signature and returns `list[ExcelTransaction]`
- [ ] `DataSession` methods are idempotent (cache verification)
- [ ] All controller tests pass: `poetry run pytest tests/controllers/`
- [ ] Pyright clean: `poetry run pyright quicken_helper/controllers/`

---

## API Contracts (Promises to Other Agents)

### Agent A commits to providing:

**1. DataSession public API:**
```python
# Location: quicken_helper/controllers/data_session.py
@dataclass
class DataSession:
    qif_path: Path | None
    qif_txns: list[ITransaction]
    excel_path: Path | None
    excel_txns: list[ExcelTransaction]
    
    def load_qif(self, path: Path, *, encoding: str = "utf-8") -> list[ITransaction]
    def load_excel(self, path: Path) -> list[ExcelTransaction]
```

**2. Logging infrastructure:**
- All modules listed above have `log = logging.getLogger(__name__)`
- Critical operations wrapped with appropriate log levels
- Exception paths include `log.exception()` calls

**3. Type safety:**
- All modified code passes Pyright
- Return types are concrete (no `Any` leaks)
- `ITransaction` and `ExcelTransaction` types are used consistently

### Agent B will consume:
- `DataSession` class for optional tab integration
- Relies on stable `load_qif()` and `load_excel()` signatures

### Agent C works independently but may reference:
- Logging patterns established here
- `DataSession` as optional integration point later

---

## Testing Strategy

### Existing Tests to Maintain (must stay green)

**Controller tests:**
- `tests/controllers/test_match_excel.py` - all tests pass
- `tests/controllers/test_match_session.py` - all tests pass
- `tests/controllers/test_qif_loader_protocol.py` - all tests pass
- `tests/controllers/test_category_match_session.py` - all tests pass

**GUI tests:**
- `tests/gui_viewers/test_convert_tab.py` - all tests pass
- `tests/gui_viewers/test_merge_tab.py` - all tests pass
- `tests/gui_viewers/test_app.py` - all tests pass

### New Tests (optional but recommended)

If you add `excel_groups_to_txns()` as a standalone function:
```python
# tests/controllers/test_match_excel.py
def test_excel_groups_to_txns_converts_groups_to_transactions():
    """
    Verify excel_groups_to_txns converts ExcelTxnGroup list to ExcelTransaction list.
    
    Follows unit-test-policy.md: isolated, deterministic, clear failure messages.
    """
    # Arrange
    groups = [...]  # Create test groups
    
    # Act
    txns = excel_groups_to_txns(groups)
    
    # Assert
    assert len(txns) == len(groups)
    assert all(isinstance(t, ExcelTransaction) for t in txns)
```

### Logging Verification (manual)

Run the GUI and verify logs appear:
```powershell
poetry run python -m quicken_helper.gui_viewers.app
# Interact with Convert/Merge/Probe tabs
# Check console output for log messages
```

---

## Files Modified Summary

### Primary modifications:
1. `quicken_helper/gui_viewers/convert_tab.py` - add logging
2. `quicken_helper/gui_viewers/probe_tab.py` - add logging
3. `quicken_helper/controllers/match_excel.py` - add logging + verify/create helper
4. `quicken_helper/controllers/match_session.py` - add logging
5. `quicken_helper/controllers/qif_loader.py` - verify typing
6. `quicken_helper/controllers/data_session.py` - verify API, add logging

### Files to read (context):
- `quicken_helper/data_model/interfaces/i_transaction.py`
- `quicken_helper/data_model/excel/__init__.py` (ExcelTransaction)
- `tests/controllers/*.py` (existing test patterns)

---

## Completion Criteria

**Before opening PR:**

1. **All tools pass:**
   - [ ] `poetry run black .` - no changes needed
   - [ ] `poetry run ruff check` - zero errors
   - [ ] `poetry run pyright` - zero errors in modified files
   - [ ] `poetry run pytest` - all tests pass (not just controllers/gui)

2. **Code quality:**
   - [ ] No new `Any` types introduced
   - [ ] All public functions have type annotations
   - [ ] Logging calls use `%s` formatting (not f-strings)
   - [ ] Exception handling includes `log.exception()` before UI errors

3. **API contracts:**
   - [ ] `DataSession` API matches promised signature
   - [ ] Return types are `list[ITransaction]` / `list[ExcelTransaction]` (not generators)
   - [ ] Methods are idempotent (cache behavior verified)

4. **Documentation:**
   - [ ] Update this file with "Status: ✅ Complete"
   - [ ] Document any deviations from plan in PR description
   - [ ] List any new functions added in PR description

5. **Integration readiness:**
   - [ ] No breaking changes to existing APIs
   - [ ] Agent B can import `DataSession` and use it immediately
   - [ ] Logging patterns are clear for other agents to follow

---

## Merge Strategy

**Target branch:** `master` (or current active development branch)

**Merge order:** First (Agent A should merge before B)

**Why:** Agent B depends on stable `DataSession` API. Agent C is independent but may benefit from logging patterns.

**Pre-merge checklist:**
- [ ] All completion criteria met
- [ ] PR opened with clear description
- [ ] CI passes (if applicable)
- [ ] Code review requested (if applicable)
- [ ] No merge conflicts with master

---

## Communication & Handoff

**When Agent A completes:**

1. Update `docs/agent-work-allocation.md` status to "✅ Complete"
2. Post commit SHA where `DataSession` API is stable
3. Notify Agent B they can begin (dependency satisfied)
4. Document any lessons learned or unexpected issues

**If blocked:**
- Document blocker in `docs/agent-work-allocation.md`
- Reach out to project lead or other agents if shared files are affected

---

## Quick Reference Commands

```powershell
# Start work
git checkout -b refactor/logging-foundation

# Run full workflow (after each change)
poetry run black .
poetry run ruff check
poetry run pyright
poetry run pytest

# Run targeted tests (faster iteration)
poetry run pytest tests/controllers/ -v
poetry run pytest tests/gui_viewers/ -v

# Type-check specific module
poetry run pyright quicken_helper/controllers/data_session.py

# Launch GUI for manual verification
poetry run python -m quicken_helper.gui_viewers.app
```

---

## Status Tracking

**Current status:** 🟡 Ready to Start  
**Branch created:** [ ]  
**Phase 5 complete:** [ ]  
**Phase 6.2 complete:** [ ]  
**PR opened:** [ ]  
**PR merged:** [ ]  

**Last updated:** 2025-01-19  
**Agent assigned:** _[Your Name/ID]_