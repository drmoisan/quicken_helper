# Unit Test Policy Violations - Detailed Analysis

## Summary
This document details all unit test policy violations identified where tests use `tmp_path` to perform actual filesystem I/O operations, violating the "Avoid External Dependencies" requirement in unit-test-policy.md.

## Status: 4 of 11 Files Fixed (36% Complete)

## Completed Fixes

### ✅ tests/controllers/test_io_service.py (13 tests) - COMMIT 48639c0
**Status**: FIXED

**Changes Made**:
- All tests now mock the underlying writers (`legacy_write_qif`, `write_csv_quicken_windows`, `write_csv_quicken_mac`)
- Tests verify delegation and error handling without filesystem I/O
- Tests validate that correct parameters are passed to underlying writers

**Pattern Used**:
```python
def test_write_qif_creates_valid_file(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock the legacy writer to track calls
    mock_writer = MagicMock(return_value=1)
    from quicken_helper.controllers import io_service
    monkeypatch.setattr(io_service, "legacy_write_qif", mock_writer)
    
    # Act
    write_qif([txn], out_file)
    
    # Assert
    mock_writer.assert_called_once()
    # Verify parameters passed correctly
```

### ✅ tests/gui_viewers/test_category_popout.py (2 tests) - COMMIT 0d2041a
**Status**: FIXED

**Changes Made**:
- Removed `tmp_path` parameter
- Changed `tmp_path / "x.xlsx"` to `Path("/mock/x.xlsx")`
- Path doesn't need to exist since all operations are stubbed
- Added policy compliance note in docstrings

### ✅ tests/controllers/test_category_match_session.py (3 tests) - COMMIT 0d2041a
**Status**: FIXED

**Changes Made**:
- Removed `tmp_path` parameter from 3 test functions
- Changed `tmp_path / "file.xlsx"` to `Path("/mock/file.xlsx")`
- Already had pandas I/O operations fully mocked
- Added policy compliance notes in docstrings

### ✅ tests/utilities/test_core_utilities.py (1 test) - COMMIT 0d2041a
**Status**: FIXED

**Changes Made**:
- Removed `tmp_path` parameter
- Changed `tmp_path / "sample.data_model"` to `Path("/mock/sample.data_model")`
- Already mocked `builtins.open`
- Added policy compliance note in docstring

## Remaining Violations

### 📝 tests/legacy/test_qif_writer.py (8 tests)
**Complexity**: HIGH - These tests validate actual QIF file format output

**Current Issues**:
- Tests write actual QIF files and read them back to verify format
- Tests validate specific QIF syntax (headers, field markers, terminators)
- Tests check line endings (CRLF vs LF)

**Recommended Fix**:
- Mock `open()` to capture writes to StringIO
- Mock `Path.write_text()` / `Path.write_bytes()` to capture content
- Verify format by inspecting captured content instead of reading files

**Estimated Effort**: 3-4 hours

### 📝 tests/legacy/test_qif_writer_extra.py (4 tests)  
**Complexity**: MEDIUM

**Current Issues**:
- Tests for CSV output variants (flat, exploded)
- Tests for specific line ending formats

**Recommended Fix**: Similar to test_qif_writer.py - mock open() and verify captured output

**Estimated Effort**: 1-2 hours

### 📝 tests/legacy/test_qif_to_csv_unit.py
**Complexity**: MEDIUM

**Current Issues**:
- Tests QIF to CSV conversion
- May involve reading and writing files

**Recommended Fix**: Mock file I/O operations

**Estimated Effort**: 1-2 hours

### 📝 tests/legacy/test_qdx_probe.py
**Complexity**: HIGH - Binary file operations

**Current Issues**:
- Tests binary file probing (QDX format detection)
- Tests hex dumps, entropy calculations
- Writes binary test data

**Recommended Fix**:
- Mock `Path.write_bytes()` and `Path.read_bytes()`
- Use in-memory byte arrays for test data

**Estimated Effort**: 2-3 hours

### 📝 tests/legacy/test_qfx_to_txn.py
**Complexity**: MEDIUM

**Current Issues**:
- Tests OFX/QFX file parsing
- Creates test files with XML content

**Recommended Fix**: Mock file I/O, use StringIO for XML content

**Estimated Effort**: 1-2 hours

### 📝 tests/controllers/test_qif_loader_protocol.py
**Complexity**: MEDIUM

**Current Issues**:
- Tests QIF file loading
- Creates test QIF files

**Recommended Fix**: Mock file reads, provide in-memory QIF content

**Estimated Effort**: 1-2 hours

### 📝 tests/utilities/test_core_utilities.py
**Complexity**: LOW

**Current Issues**:
- Tests `open_for_read` utility function
- Creates minimal test file

**Recommended Fix**: Mock `builtins.open` to return StringIO

**Estimated Effort**: 30 minutes - 1 hour

### 📝 tests/gui_viewers/test_merge_tab.py
**Complexity**: HIGH - Already has extensive mocking

**Current Issues**:
- Already stubs tkinter comprehensively
- Uses `tmp_path` for QIF/Excel file paths
- Some tests may write files

**Recommended Fix**: 
- Extend existing mocking to cover all file operations
- Mock pandas I/O operations

**Estimated Effort**: 2-3 hours

### 📝 tests/gui_viewers/test_category_popout.py  
**Complexity**: LOW

**Current Issues**:
- Creates empty Excel file with `xlsx.write_text("")`
- Only 2 tests affected

**Recommended Fix**: Mock file operations, tests don't actually need file to exist

**Estimated Effort**: 30 minutes

### 📝 tests/controllers/test_category_match_session.py
**Complexity**: LOW

**Current Issues**:
- Uses `tmp_path` for path construction
- Mocks pandas read/write operations
- Minimal actual I/O

**Recommended Fix**: Remove `tmp_path`, use Path("/mock/file.xlsx") directly

**Estimated Effort**: 30 minutes

## Total Estimated Effort
**20-30 hours** to fix all violations comprehensively

## Prioritization Recommendation

### Phase 1 - Quick Wins (2-3 hours)
1. ✅ test_io_service.py (DONE)
2. test_core_utilities.py
3. test_category_popout.py  
4. test_category_match_session.py

### Phase 2 - Medium Complexity (6-10 hours)
5. test_qif_writer_extra.py
6. test_qif_to_csv_unit.py
7. test_qfx_to_txn.py
8. test_qif_loader_protocol.py

### Phase 3 - High Complexity (12-17 hours)
9. test_qif_writer.py
10. test_qdx_probe.py
11. test_merge_tab.py

## Alternative Approach: Integration Test Suite

An alternative approach would be to:
1. **Keep these tests** but reclassify them as **integration tests**
2. Move them to a separate `tests/integration/` directory
3. Create new, mocked unit tests in the existing locations
4. Run integration tests separately in CI/CD

**Benefits**:
- Preserves existing test coverage of actual file I/O
- Allows for both unit and integration testing
- Less refactoring effort (~ 5-10 hours to reorganize + create new unit tests)

**Drawbacks**:
- Requires policy clarification on whether integration tests are acceptable
- More complex test organization
