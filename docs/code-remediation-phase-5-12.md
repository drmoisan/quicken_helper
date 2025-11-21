Here you go—same roadmap, just renumbered so it starts at **Phase 5** (and all internal references adjusted). Overall status: 🟥❌ not started.

---

## High-Level Targets 🟥❌ not started

- 🟥❌ not started **Load once, work in memory, write once**
   * 🟥❌ not started Consolidate all loading/parsing to a small set of loaders.
   * 🟥❌ not started All transforms operate on `ITransaction` / `ExcelTransaction` instances, not on raw rows/dicts.
- 🟥❌ not started **App is just wiring; tabs own behavior**
   * 🟥❌ not started Remove `app.py` shims (paths, emit vars, helper methods).
   * 🟥❌ not started Migrate shim-driven tests into tab-specific tests.
- 🟥❌ not started **Match pipeline is protocol-centric and type-safe**
   * 🟥❌ not started `MatchSession` and `match_excel.py` use shared protocols and no legacy `QIFTxnView` / "groups in the session".
- 🟥❌ not started **Logging is rich and consistent**
   * 🟥❌ not started Standard logging across tabs + controllers, good diagnostics for failures.

Codex can treat each phase as a separate PR or commit chain.

---

## Phase 5 - Logging + Diagnostics Foundation 🟥❌ not started

**Objective:** 🟥❌ not started Add consistent, low-risk logging to the GUI tabs and controllers.

### 5.1 Add module-level loggers 🟥❌ not started

**Files:**

* 🟥❌ not started `quicken_helper/gui_viewers/convert_tab.py`
* 🟥❌ not started `quicken_helper/gui_viewers/probe_tab.py`
* 🟥❌ not started Verify `merge_tab.py` already has a logger; if not, add it there too.
* 🟥❌ not started Optionally: `quicken_helper/controllers/match_excel.py`, `match_session.py`, loaders/writers.

**Tasks:**

1. 🟥❌ not started At top of each module add:

   ```python
   import logging
   log = logging.getLogger(__name__)
   ```
2. 🟥❌ not started Wrap critical operations with `log.debug` / `log.info`, e.g. input/output paths selected, emit mode, start/finish of long operations.
3. 🟥❌ not started On exception paths where a `messagebox` or similar is shown, log with `log.exception("...")` before surfacing UI error messages.

**Invariants:**

* 🟥❌ not started No behavior change; tests remain green.
* 🟥❌ not started No new `Any` leaks; log calls should not force type loosening.

---

## Phase 6 - Centralized Loading & In-Memory "DataSession" 🟥❌ not started

**Objective:** 🟥❌ not started Stop re-loading files in multiple places; create a shared in-memory model.

### 6.1 Introduce a `DataSession` controller 🟥❌ not started

**New module:**

* 🟥❌ not started `quicken_helper/controllers/data_session.py`

**Responsibilities:**

* 🟥❌ not started Define fields for bank/excel paths and transaction lists using protocol types.
* 🟥❌ not started `load_bank_qif(path: Path, encoding: str = "utf-8") -> None`
* 🟥❌ not started `load_excel(path: Path) -> None`
* 🟥❌ not started Optional `clear()` to reset.

**Constraints:**

* 🟥❌ not started `DataSession` does not know about GUI or tabs.
* 🟥❌ not started All types concrete and Pylance-clean.

### 6.2 Convert existing loaders to feed `DataSession` 🟥❌ not started

**Files:**

* 🟥❌ not started `controllers/match_excel.py`
* 🟥❌ not started QIF loader(s) (e.g., `q_wrapper/q_file.py` and helpers)

**Tasks:**

1. 🟥❌ not started Standardize the QIF loader to produce `list[ITransaction]`.
2. 🟥❌ not started In `match_excel.py`, ensure helpers convert groups to protocol objects; add `excel_groups_to_txns` (or equivalent).

**Invariants:**

* 🟥❌ not started Existing tests for loaders still pass.
* 🟥❌ not started Tabs do not use `DataSession` yet; additive change.

---

## Phase 7 - Refactor Tabs to Use `DataSession` (Opt-In) 🟥❌ not started

**Objective:** 🟥❌ not started Allow tabs to optionally use the shared in-memory data without breaking current usage.

### 7.1 Allow tabs to accept an optional session 🟥❌ not started

**Files:**

* 🟥❌ not started `gui_viewers/merge_tab.py`
* 🟥❌ not started `gui_viewers/convert_tab.py`
* 🟥❌ not started `gui_viewers/probe_tab.py`
* 🟥❌ not started `gui_viewers/app.py` (to pass the session when creating tabs)

**Tasks:**

1. 🟥❌ not started Update tab constructors to accept `session: DataSession | None = None` and store as `self._session`.
2. 🟥❌ not started When files are chosen via the UI, use `self._session` to load/reuse data when provided; keep fallback behavior for `session=None`.

**Invariants:**

* 🟥❌ not started `app.py` builds a single `DataSession` and passes it to tabs.
* 🟥❌ not started All tab tests still pass.

---

## Phase 8 - `app.py` Shim Removal + Test Migration 🟥❌ not started

**Objective:** 🟥❌ not started Make `App` only wire the UI and session; remove behavioral shims.

### 8.1 Identify and remove shims from `app.py` 🟥❌ not started

**Likely shims:**

* 🟥❌ not started Public attributes like `app.in_path`, `app.out_path`, `app.emit_var`.
* 🟥❌ not started Methods like `_update_output_extension`, `_parse_payee_filters`, `_run`, `_m_normalize_categories`, etc.

**Tasks:**

1. 🟥❌ not started Move path/extension logic into `ConvertTab`.
2. 🟥❌ not started Move payee filter parsing into `ConvertTab` or a shared helper.
3. 🟥❌ not started Normalize categories delegation handled directly in `MergeTab`.
4. 🟥❌ not started In `App.__init__`, only create `DataSession`, `Notebook`, and tabs; remove shim exposure.

**Invariants:**

* 🟥❌ not started App still runs; tabs own behavior.
* 🟥❌ not started No references to app-level shims remain.

### 8.2 Migrate and trim tests in `tests/gui_viewers/test_app.py` 🟥❌ not started

**Actions:**

1. 🟥❌ not started Keep but trim initialization test to wiring only.
2. 🟥❌ not started Migrate ConvertTab-specific tests (`_update_output_extension`, `_parse_payee_filters`, run path/overwrite behaviors) into `test_convert_tab.py` with direct tab instantiation and mocks.
3. 🟥❌ not started Eliminate redundant tests (e.g., `test_m_normalize_categories_delegates_to_merge_tab`, redundant QIF-write tests).

**Invariants:**

* 🟥❌ not started `pytest tests/gui_viewers` remains green.
* 🟥❌ not started No tests reference `App` shims.

---

## Phase 9 - Align `match_excel.py` with `MatchSession` and the New Flow 🟥❌ not started

**Objective:** 🟥❌ not started Modernize `match_excel.py` to match the protocol-centric `MatchSession` API and be Pylance-clean.

### 9.1 Remove legacy types and maps 🟥❌ not started

**Files:**

* 🟥❌ not started `controllers/match_excel.py`
* 🟥❌ not started `controllers/match_session.py` (for imports and API consistency)

**Tasks:**

1. 🟥❌ not started Delete/stop importing `QIFTxnView`, `QIFItemKey`, and any `session.excel_groups` or `session.qif_to_excel_group` references.
2. 🟥❌ not started Verify `MatchSession` exposes protocol-centric fields (`bank_txns`, `excel_txns`, `pairs`, `unmatched_bank`, `unmatched_excel`; optional `auto_match`).

### 9.2 Re-implement `build_matched_only_txns(session)` with new API 🟥❌ not started

**Target signature:** 🟥❌ not started ensure `build_matched_only_txns(session: MatchSession) -> list[ITransaction]`.

**Implementation outline:** 🟥❌ not started build set/dict for indices, return matched bank transactions without mutating session.

**Invariants:** 🟥❌ not started Type annotations concrete; no session mutation.

### 9.3 Modernize `run_excel_qif_merge(...)` 🟥❌ not started

**Tasks:**

1. 🟥❌ not started Load QIF as `list[ITransaction]` via canonical loader.
2. 🟥❌ not started Load Excel rows/groups, map to protocol transactions.
3. 🟥❌ not started Build `MatchSession` and run matching; return `(pairs, unmatched_bank, unmatched_excel)`.
4. 🟥❌ not started Keep function pure (no writes).

### 9.4 Decide how writing QIF uses `MatchSession` (and update `MergeTab`) 🟥❌ not started

**Options:**

* 🟥❌ not started Option A: Writer accepts `ITransaction` directly; `MergeTab` uses matched-only or full bank list then calls `write_qif`.
* 🟥❌ not started Option B: Convert to legacy dicts right before writing; keep protocols elsewhere.

**Invariants:** 🟥❌ not started `MergeTab` no longer expects obsolete session fields; match/QIF tests pass.

---

## Phase 10 - Move Transformations Fully "In-Memory" 🟥❌ not started

**Objective:** 🟥❌ not started Ensure all non-I/O operations are transformations over already-loaded objects from `DataSession`.

### 10.1 Audit tabs for direct file reads 🟥❌ not started

**Tasks:**

1. 🟥❌ not started Replace ad-hoc file parsing with `DataSession` access (`bank_txns`, `excel_txns`).
2. 🟥❌ not started Maintain fallback behavior for tests using `session=None`.

### 10.2 Centralize write paths 🟥❌ not started

**Module:**

* 🟥❌ not started `quicken_helper/controllers/io_service.py`

**Responsibilities:**

* 🟥❌ not started `write_qif(txns: Sequence[ITransaction], path: Path, encoding: str = "utf-8")`
* 🟥❌ not started `write_csv(txns: Sequence[ITransaction], path: Path, dialect/options)`

**Invariants:** 🟥❌ not started Tabs call services instead of writing directly; options passed explicitly.

---

## Phase 11 - Richer Error Reporting & UX Hooks 🟥❌ not started

**Objective:** 🟥❌ not started Provide better visibility when things go wrong.

**Tasks:**

1. 🟥❌ not started Collect parse stats (lines read, parsed/skipped, sample errors).
2. 🟥❌ not started Expose structured error/summary from controllers to tabs.
3. 🟥❌ not started Tabs show UI messages while logs capture full details.

**Invariants:** 🟥❌ not started Controllers remain UI-agnostic; tabs translate to UI.

---

## Phase 12 - Future Enhancements (Optional / Later) 🟥❌ not started

1. 🟥❌ not started **Cross-reference registry** - build module to map transactions across sources using keys/heuristics.
2. 🟥❌ not started **Backgroundable tasks / progress hooks** - structure long-running operations for future progress reporting.
3. 🟥❌ not started **Configurable pipelines** - allow named "recipes" for conversion and merge steps.

---

## How Codex Can Use This Roadmap 🟥❌ not started

When you feed this to Codex in VSCode, you can ask it to:

1. 🟥❌ not started **Compare current code vs roadmap** (e.g., "Show me where Phase 8.1 is already done and where it's not.")
2. 🟥❌ not started **Implement phase by phase** (e.g., "Implement Phase 7.1 exactly as described." or "Refactor `match_excel.py` per Phase 9`...")

This should now slot cleanly after the existing "Phase 1-4" remediation roadmap.
