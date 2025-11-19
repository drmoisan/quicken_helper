# Agent C: Match Pipeline Modernization

**Phase:** 9 (Align match_excel.py with MatchSession and New Flow)  
**Branch:** `refactor/match-pipeline`  
**Estimated Effort:** Large (3-4 days)  
**Status:** 🟢 Ready to Start  
**Dependencies:** None (can start immediately, parallel with Agent A)

---

## Mission

Modernize the match pipeline to be fully protocol-centric and type-safe. Remove legacy types (`QIFTxnView`, `QIFItemKey`), rebuild match functions around `MatchSession` API, and establish clean QIF writer path from protocols.

---

## Core Working Instructions

**MUST READ before starting work:**

1. **[code-change.instructions.md](../.github/code-change.instructions.md)** - Policy for every code change
2. **[unit-test-policy.md](unit-test-policy.md)** - Standards for testing
3. **[developer-tooling.md](developer-tooling.md)** - Required workflow commands
4. **[code-remediation-phase-5-12.md](code-remediation-phase-5-12.md)** - Full roadmap context (Phase 9 details)

**Required workflow after EVERY change:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest`

If any step fails, fix it before proceeding.

---

## Phase 9.1: Remove Legacy Types and Maps

### Objective
Eliminate `QIFTxnView`, `QIFItemKey`, and associated legacy maps from the match pipeline.

### Task 9.1.1: Audit Current Usage

**Files to search:**
- `quicken_helper/controllers/match_excel.py`
- `quicken_helper/controllers/match_session.py`
- `quicken_helper/legacy/qif_txn_view.py` (reference only)
- `quicken_helper/legacy/qif_item_key.py` (reference only)

**Search patterns:**
```powershell
rg "QIFTxnView" quicken_helper/controllers/
rg "QIFItemKey" quicken_helper/controllers/
rg "excel_groups" quicken_helper/controllers/match_session.py
rg "qif_to_excel_group" quicken_helper/controllers/match_session.py
```

**Create removal plan:**
- [ ] List all imports of `QIFTxnView` / `QIFItemKey`
- [ ] List all variables/fields using these types
- [ ] List all functions accepting/returning these types
- [ ] Identify tests that reference these types

### Task 9.1.2: Remove Legacy Imports from match_excel.py

**File:** `quicken_helper/controllers/match_excel.py`

**Remove (if present):**
```python
from quicken_helper.legacy.qif_txn_view import QIFTxnView
from quicken_helper.legacy.qif_item_key import QIFItemKey
```

**Verify no other references remain:**
```powershell
rg "QIFTxnView|QIFItemKey" quicken_helper/controllers/match_excel.py
# Should return no results after removal
```

### Task 9.1.3: Remove Legacy Session Attributes

**File:** `quicken_helper/controllers/match_session.py`

**Remove (if present):**
```python
# Old attributes to remove:
excel_groups: list[ExcelTxnGroup]
qif_to_excel_group: dict[Any, ExcelTxnGroup]
```

**Verify `MatchSession` has clean protocol-based API:**
```python
@dataclass
class MatchSession:
    bank_txns: list[ITransaction]  # QIF/bank side
    excel_txns: list[ExcelTransaction]  # Excel side
    pairs: list[tuple[ITransaction, ExcelTransaction]]  # Matched pairs
    unmatched_bank: list[ITransaction]
    unmatched_excel: list[ExcelTransaction]
    
    # Methods (verify these exist and are type-clean):
    def auto_match(self) -> None: ...
    # Other methods as needed
```

**Invariants:**
- All types concrete (no `Any` in public API)
- All attributes use protocol types (`ITransaction`, `ExcelTransaction`)
- No legacy view/key types remain

---

## Phase 9.2: Re-implement build_matched_only_txns

### Objective
Create type-safe function that extracts bank transactions participating in matches.

### Task 9.2.1: Implement build_matched_only_txns

**File:** `quicken_helper/controllers/match_excel.py`

**Add new function:**
```python
from quicken_helper.data_model.interfaces import ITransaction
from quicken_helper.controllers.match_session import MatchSession

def build_matched_only_txns(session: MatchSession) -> list[ITransaction]:
    """
    Return bank-side transactions that participate in session.pairs.
    
    Preserves order of transactions in session.bank_txns.
    Uses identity-based lookup to avoid O(n²) comparison.
    
    Args:
        session: MatchSession with pairs populated
        
    Returns:
        List of bank transactions that have matches, in original order
    """
    # Build set of bank transaction identities from pairs
    matched_ids = {id(bank_txn) for bank_txn, _ in session.pairs}
    
    # Filter bank_txns to only matched ones, preserving order
    return [txn for txn in session.bank_txns if id(txn) in matched_ids]
```

**Alternative implementation (index-based):**
```python
def build_matched_only_txns(session: MatchSession) -> list[ITransaction]:
    """Return bank-side transactions that participate in session.pairs."""
    # Create index map for O(1) lookup
    bank_txn_to_idx = {id(txn): idx for idx, txn in enumerate(session.bank_txns)}
    
    # Collect indices of matched transactions
    matched_indices = {
        bank_txn_to_idx[id(bank_txn)] 
        for bank_txn, _ in session.pairs
    }
    
    # Return in sorted index order
    return [
        session.bank_txns[idx]
        for idx in sorted(matched_indices)
    ]
```

**Choose implementation based on:**
- Performance needs (both are O(n))
- Preference for identity vs index tracking
- Team coding style

### Task 9.2.2: Add Unit Tests for build_matched_only_txns

**File:** `tests/controllers/test_match_excel.py`

**Add comprehensive tests:**

```python
def test_build_matched_only_txns_returns_matched_bank_transactions():
    """
    Verify build_matched_only_txns returns only bank txns with matches.
    
    Tests positive flow with valid matches. Follows unit-test-policy.md.
    """
    # Arrange
    bank_txn1 = _make_transaction(date="2025-01-01", amount=100)
    bank_txn2 = _make_transaction(date="2025-01-02", amount=200)
    bank_txn3 = _make_transaction(date="2025-01-03", amount=300)
    
    excel_txn1 = _make_excel_transaction(date="2025-01-01", amount=100)
    excel_txn2 = _make_excel_transaction(date="2025-01-03", amount=300)
    
    session = MatchSession(
        bank_txns=[bank_txn1, bank_txn2, bank_txn3],
        excel_txns=[excel_txn1, excel_txn2],
        pairs=[(bank_txn1, excel_txn1), (bank_txn3, excel_txn2)],
        unmatched_bank=[bank_txn2],
        unmatched_excel=[],
    )
    
    # Act
    result = build_matched_only_txns(session)
    
    # Assert
    assert len(result) == 2, "Should return 2 matched transactions"
    assert result[0] is bank_txn1, "First matched txn should be bank_txn1"
    assert result[1] is bank_txn3, "Second matched txn should be bank_txn3"


def test_build_matched_only_txns_preserves_order():
    """Verify matched transactions returned in original bank_txns order."""
    # Arrange
    txns = [_make_transaction(date=f"2025-01-{i:02d}", amount=i*100) for i in range(1, 6)]
    excel = [_make_excel_transaction(date=f"2025-01-{i:02d}", amount=i*100) for i in [2, 4]]
    
    session = MatchSession(
        bank_txns=txns,
        excel_txns=excel,
        pairs=[(txns[3], excel[1]), (txns[1], excel[0])],  # Out of order pairs
        unmatched_bank=[txns[0], txns[2], txns[4]],
        unmatched_excel=[],
    )
    
    # Act
    result = build_matched_only_txns(session)
    
    # Assert
    assert result == [txns[1], txns[3]], "Should preserve bank_txns order"


def test_build_matched_only_txns_empty_pairs():
    """Verify empty list returned when no matches exist."""
    # Arrange
    session = MatchSession(
        bank_txns=[_make_transaction(date="2025-01-01", amount=100)],
        excel_txns=[_make_excel_transaction(date="2025-01-02", amount=200)],
        pairs=[],
        unmatched_bank=[],
        unmatched_excel=[],
    )
    
    # Act
    result = build_matched_only_txns(session)
    
    # Assert
    assert result == [], "Should return empty list when no pairs"


def test_build_matched_only_txns_does_not_mutate_session():
    """Verify function is pure and does not modify session."""
    # Arrange
    bank_txns = [_make_transaction(date="2025-01-01", amount=100)]
    excel_txns = [_make_excel_transaction(date="2025-01-01", amount=100)]
    pairs = [(bank_txns[0], excel_txns[0])]
    
    session = MatchSession(
        bank_txns=bank_txns,
        excel_txns=excel_txns,
        pairs=pairs,
        unmatched_bank=[],
        unmatched_excel=[],
    )
    
    original_bank_count = len(session.bank_txns)
    original_pair_count = len(session.pairs)
    
    # Act
    build_matched_only_txns(session)
    
    # Assert
    assert len(session.bank_txns) == original_bank_count, "Should not mutate bank_txns"
    assert len(session.pairs) == original_pair_count, "Should not mutate pairs"
```

**Run tests:**
```powershell
poetry run pytest tests/controllers/test_match_excel.py::test_build_matched_only_txns -v
```

---

## Phase 9.3: Modernize run_excel_qif_merge

### Objective
Refactor to return protocol transactions, not legacy dicts. No write operations.

### Task 9.3.1: Update run_excel_qif_merge Signature

**File:** `quicken_helper/controllers/match_excel.py`

**New signature:**
```python
from pathlib import Path
from quicken_helper.data_model.interfaces import ITransaction
from quicken_helper.data_model.excel import ExcelTransaction

def run_excel_qif_merge(
    qif_in: Path,
    xlsx: Path,
    *,
    encoding: str = "utf-8",
) -> tuple[
    list[tuple[ITransaction, ExcelTransaction]],  # pairs
    list[ITransaction],  # unmatched_bank
    list[ExcelTransaction],  # unmatched_excel
]:
    """
    Parse QIF and Excel files, match transactions, return results.
    
    Does NOT write output. Returns structured match results for caller
    to process (write, display, etc.).
    
    Args:
        qif_in: Path to QIF file
        xlsx: Path to Excel file
        encoding: Text encoding for QIF file
        
    Returns:
        Tuple of (pairs, unmatched_bank, unmatched_excel)
    """
    # Implementation in next task
```

### Task 9.3.2: Implement run_excel_qif_merge Body

**File:** `quicken_helper/controllers/match_excel.py`

**Implementation:**
```python
def run_excel_qif_merge(
    qif_in: Path,
    xlsx: Path,
    *,
    encoding: str = "utf-8",
) -> tuple[
    list[tuple[ITransaction, ExcelTransaction]],
    list[ITransaction],
    list[ExcelTransaction],
]:
    """Parse QIF and Excel files, match transactions, return results."""
    # 1. Load QIF as list[ITransaction]
    from quicken_helper.controllers.qif_loader import load_transactions_protocol
    bank_txns = list(load_transactions_protocol(qif_in, encoding=encoding))
    
    # 2. Load Excel as list[ExcelTransaction]
    from quicken_helper.data_model.excel import map_group_to_excel_txn
    rows = load_excel_rows(xlsx)
    groups = group_excel_rows(rows)
    excel_txns = [map_group_to_excel_txn(g) for g in groups]
    
    # 3. Build MatchSession and run matching
    session = MatchSession(
        bank_txns=bank_txns,
        excel_txns=excel_txns,
        pairs=[],
        unmatched_bank=list(bank_txns),  # Initially all unmatched
        unmatched_excel=list(excel_txns),
    )
    session.auto_match()  # Populates pairs, updates unmatched lists
    
    # 4. Return structured results
    return (session.pairs, session.unmatched_bank, session.unmatched_excel)
```

**Verify:**
- No write operations (`write_qif`, file opens in write mode)
- All return types concrete and protocol-based
- Pyright clean

### Task 9.3.3: Update Tests for run_excel_qif_merge

**File:** `tests/controllers/test_match_excel.py`

**Update existing tests:**
- Find tests calling `run_excel_qif_merge`
- Update assertions to expect tuple return
- Remove expectations of file writes (those move to separate tests)

**Example:**
```python
def test_run_excel_qif_merge_returns_matched_pairs(tmp_path):
    """
    Verify run_excel_qif_merge returns matched transaction pairs.
    
    Tests core matching logic. Follows unit-test-policy.md.
    """
    # Arrange
    qif_file = tmp_path / "bank.qif"
    qif_file.write_text("!Type:Bank\nD01/01/2025\nT100.00\n^\n")
    
    excel_file = tmp_path / "excel.xlsx"
    _write_test_excel(excel_file, [{"Date": "01/01/2025", "Amount": 100.00}])
    
    # Act
    pairs, unmatched_bank, unmatched_excel = run_excel_qif_merge(qif_file, excel_file)
    
    # Assert
    assert len(pairs) == 1, "Should match 1 pair"
    bank_txn, excel_txn = pairs[0]
    assert bank_txn.amount == 100, "Bank amount should be 100"
    assert excel_txn.amount == 100, "Excel amount should be 100"
    assert len(unmatched_bank) == 0, "No unmatched bank txns"
    assert len(unmatched_excel) == 0, "No unmatched excel txns"
```

---

## Phase 9.4: QIF Writer Path Decision & Implementation

### Objective
Establish single, type-safe path from `MatchSession` → QIF output.

### Task 9.4.1: Choose Writer Strategy

**Option A: Writer accepts ITransaction directly**
- Implement/modify writer: `write_qif(txns: list[ITransaction], path: Path)`
- Writer inspects protocol attributes (`date`, `amount`, `payee`, etc.)
- Pro: Keeps everything in protocols
- Con: May need adapter if QIF writer expects dicts

**Option B: Convert to dicts before writing**
- Add helper: `to_qif_dict(txn: ITransaction) -> dict[str, Any]`
- Convert at call site: `dicts = [to_qif_dict(t) for t in txns]`
- Pass dicts to existing writer
- Pro: Minimal writer changes
- Con: Extra conversion step

**Recommendation: Option A (protocol-native writer)**

**Document decision:** Add comment in this file and PR description.

### Task 9.4.2: Implement/Verify QIF Writer (Option A)

**File:** `quicken_helper/legacy/qif_writer.py` (or create new writer)

**Target signature:**
```python
from pathlib import Path
from quicken_helper.data_model.interfaces import ITransaction

def write_qif(
    transactions: list[ITransaction],
    path: Path,
    *,
    encoding: str = "utf-8",
) -> None:
    """
    Write transactions to QIF file.
    
    Args:
        transactions: List of transactions implementing ITransaction
        path: Output file path
        encoding: Text encoding
    """
    with open(path, "w", encoding=encoding) as f:
        # Write headers
        f.write("!Type:Bank\n")
        
        # Write each transaction
        for txn in transactions:
            _write_transaction(f, txn)
        
def _write_transaction(f: TextIO, txn: ITransaction) -> None:
    """Write single transaction in QIF format."""
    if txn.date:
        f.write(f"D{txn.date.strftime('%m/%d/%Y')}\n")
    if txn.amount is not None:
        f.write(f"T{txn.amount}\n")
    if txn.payee:
        f.write(f"P{txn.payee}\n")
    if txn.memo:
        f.write(f"M{txn.memo}\n")
    if txn.category:
        f.write(f"L{txn.category}\n")
    if txn.cleared_status:
        f.write(f"C{txn.cleared_status.value}\n")
    # Handle splits if present
    if hasattr(txn, 'splits') and txn.splits:
        for split in txn.splits:
            _write_split(f, split)
    f.write("^\n")  # End of transaction
```

**Test writer:**
```python
# tests/legacy/test_qif_writer.py (or new file)
def test_write_qif_protocol_transactions(tmp_path):
    """
    Verify write_qif handles ITransaction protocol objects.
    
    Tests protocol-based writer. Follows unit-test-policy.md.
    """
    # Arrange
    from datetime import date
    from decimal import Decimal
    txn = _make_transaction(
        date=date(2025, 1, 1),
        amount=Decimal("100.00"),
        payee="Test Payee",
        memo="Test Memo",
    )
    out_file = tmp_path / "output.qif"
    
    # Act
    write_qif([txn], out_file)
    
    # Assert
    content = out_file.read_text()
    assert "!Type:Bank" in content
    assert "D01/01/2025" in content
    assert "T100.00" in content
    assert "PTest Payee" in content
    assert "MTest Memo" in content
    assert "^" in content
```

### Task 9.4.3: Update MergeTab to Use New Writer Path

**File:** `quicken_helper/gui_viewers/merge_tab.py`

**Find write operation (search for "write" or "emit"):**
```python
# Old pattern (likely):
write_qif(txn_dicts, out_path)  # dicts
```

**New pattern:**
```python
from quicken_helper.legacy.qif_writer import write_qif
from quicken_helper.controllers.match_excel import build_matched_only_txns

# In merge tab write method:
def _write_qif_output(self, path: Path, only_matched: bool) -> None:
    """Write QIF output from current match session."""
    if only_matched:
        txns = build_matched_only_txns(self._session)
    else:
        txns = self._session.bank_txns  # All transactions
    
    write_qif(txns, path, encoding=self._encoding)
```

**Invariants:**
- No `session.apply_updates()` calls (if that pattern existed)
- No `session.txns` references (use `bank_txns` instead)
- Type annotations concrete

---

## API Contracts (Promises to Other Agents)

### Agent C commits to:

**1. MatchSession clean protocol API:**
```python
@dataclass
class MatchSession:
    bank_txns: list[ITransaction]
    excel_txns: list[ExcelTransaction]
    pairs: list[tuple[ITransaction, ExcelTransaction]]
    unmatched_bank: list[ITransaction]
    unmatched_excel: list[ExcelTransaction]
    
    def auto_match(self) -> None: ...
```

**2. Match functions:**
```python
def build_matched_only_txns(session: MatchSession) -> list[ITransaction]:
    """Return bank transactions participating in pairs."""

def run_excel_qif_merge(
    qif_in: Path, xlsx: Path, *, encoding: str = "utf-8"
) -> tuple[list[tuple[...]], list[ITransaction], list[ExcelTransaction]]:
    """Parse, match, return results (no write)."""
```

**3. QIF writer:**
```python
def write_qif(
    transactions: list[ITransaction], path: Path, *, encoding: str = "utf-8"
) -> None:
    """Write transactions to QIF file."""
```

### Agent C does NOT depend on:
- Agent A (works independently)
- Agent B (tabs integrate later, not initially)

### Agent B will eventually consume:
- Updated `MatchSession` API (after both agents merge)
- `build_matched_only_txns()` function
- New `write_qif()` signature

---

## Testing Strategy

### Tests to Update

**Controller tests:**
- `tests/controllers/test_match_excel.py` - update for new signatures
- `tests/controllers/test_match_session*.py` - verify clean API
- Add new tests for `build_matched_only_txns`

**Writer tests:**
- `tests/legacy/test_qif_writer.py` - update for protocol objects
- Add tests verifying `ITransaction` → QIF output

**Integration tests (optional):**
- End-to-end: QIF + Excel → match → write → parse → verify

### Test Execution Strategy

**Iterative approach:**
1. Phase 9.1: Remove legacy types → run tests, fix failures
2. Phase 9.2: Add `build_matched_only_txns` → add tests, verify green
3. Phase 9.3: Refactor `run_excel_qif_merge` → update tests, verify green
4. Phase 9.4: QIF writer → update writer tests, verify green

**After each phase:**
```powershell
poetry run pytest tests/controllers/ tests/legacy/ -v
```

---

## Completion Criteria

**Before opening PR:**

1. **All tools pass:**
   - [ ] `poetry run black .` - no changes needed
   - [ ] `poetry run ruff check` - zero errors
   - [ ] `poetry run pyright` - zero errors in controllers/legacy
   - [ ] `poetry run pytest` - all tests pass

2. **Legacy removal:**
   - [ ] No `QIFTxnView` imports/references in controllers
   - [ ] No `QIFItemKey` imports/references in controllers
   - [ ] `MatchSession` has clean protocol API (verified)

3. **New functions:**
   - [ ] `build_matched_only_txns` implemented and tested (4+ tests)
   - [ ] `run_excel_qif_merge` refactored and tested
   - [ ] Return types all protocol-based (no `Any`)

4. **Writer path:**
   - [ ] `write_qif` accepts `list[ITransaction]` (or decision documented)
   - [ ] Writer tests pass with protocol objects
   - [ ] MergeTab integration updated (if Option A)

5. **Documentation:**
   - [ ] Update this file with "Status: ✅ Complete"
   - [ ] Document writer strategy choice in PR
   - [ ] Note any breaking changes or migration needed

---

## Merge Strategy

**Target branch:** `master`

**Merge order:** Can merge before or after Agent A/B (independent)

**Recommended:** Merge after Agent A, before Agent B integrates with tabs

**Why:** Provides clean match API for Agent B to consume when they update MergeTab.

---

## Communication & Handoff

**When Agent C completes:**

1. Update `docs/agent-work-allocation.md` status to "✅ Complete"
2. Post commit SHA where match API is stable
3. Notify Agent B that new match functions available
4. Document any API changes or migration notes

**If blocked:**
- Most work is independent
- If protocol definitions unclear, coordinate with project lead
- Document blockers in `docs/agent-work-allocation.md`

---

## Quick Reference Commands

```powershell
# Start work
git checkout -b refactor/match-pipeline

# Run full workflow
poetry run black .
poetry run ruff check
poetry run pyright
poetry run pytest

# Run targeted tests
poetry run pytest tests/controllers/test_match_excel.py -v
poetry run pytest tests/controllers/test_match_session.py -v
poetry run pytest tests/legacy/test_qif_writer.py -v

# Search for legacy types
rg "QIFTxnView|QIFItemKey" quicken_helper/controllers/

# Type-check specific files
poetry run pyright quicken_helper/controllers/match_excel.py
poetry run pyright quicken_helper/controllers/match_session.py
```

---

## Status Tracking

**Current status:** 🟢 Ready to Start  
**Branch created:** [ ]  
**Phase 9.1 complete:** [ ]  
**Phase 9.2 complete:** [ ]  
**Phase 9.3 complete:** [ ]  
**Phase 9.4 complete:** [ ]  
**PR opened:** [ ]  
**PR merged:** [ ]  

**Last updated:** 2025-01-19  
**Agent assigned:** _[Your Name/ID]_
