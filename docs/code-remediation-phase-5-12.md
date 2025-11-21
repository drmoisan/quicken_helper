Here you go—same roadmap, just renumbered so it starts at **Phase 5** (and all internal references adjusted). Overall status: ✅ 90% (Phases 5–11 complete; Phase 12 intentionally not started).

---

## High-Level Targets ✅ 90%

- ✅ 100% **Load once, work in memory, write once**  
   * ✅ Consolidate loading/parsing via `DataSession` + `qif_loader`/`match_excel`; tabs reuse cached data.  
   * ✅ Transforms operate on `ITransaction`/`ExcelTransaction` (protocol adapters), not raw dicts.
- ✅ 100% **App is just wiring; tabs own behavior**  
   * ✅ Removed `app.py` shims; app only wires tabs and shared session.  
   * ✅ Shim-driven tests migrated to tab-specific suites; `test_app` is wiring-only.
- ✅ 100% **Match pipeline is protocol-centric and type-safe**  
   * ✅ `MatchSession`/`match_excel` use protocol types; legacy `QIFTxnView` removed from controllers' surface (kept only in legacy helpers/tests).  
   * ✅ `build_matched_only_txns` present and used for matched-only flows.
- ✅ 90% **Logging is rich and consistent**  
   * ✅ Module loggers in tabs/controllers; key operations and exceptions logged.  
   * ✅ Parse stats surfaced in GUI logs/dialogs; exceptions logged; minimal remaining: optional structured UI pane (deferred).

Codex can treat each phase as a separate PR or commit chain.

---

## Phase 5 - Logging + Diagnostics Foundation ✅ 100%

**Objective:** Add consistent, low-risk logging to the GUI tabs and controllers.

### 5.1 Add module-level loggers ✅ 100%

**Files:** `quicken_helper/gui_viewers/convert_tab.py`, `probe_tab.py`, `merge_tab.py`, controllers (`match_excel.py`, `match_session.py`, loaders/writers).

**Tasks:**  
1. ✅ Module-level `log = logging.getLogger(__name__)` added.  
2. ✅ Critical operations and exceptions wrapped with `log.debug`/`log.info`/`log.exception`.  
3. ✅ No behavior change; tests remain green; typing intact.

---

## Phase 6 - Centralized Loading & In-Memory "DataSession" ✅ 100%

**Objective:** Stop re-loading files in multiple places; create a shared in-memory model.

### 6.1 Introduce a `DataSession` controller ✅ 100%

**File:** `quicken_helper/controllers/data_session.py`

**Status:**  
* ✅ Fields for bank/excel paths and transaction lists using protocol types; tracks parse stats for QIF loads.  
* ✅ `load_qif`/`load_excel` implemented with caching and logging.  
* ✅ DataSession is GUI-agnostic and typed.

### 6.2 Convert existing loaders to feed `DataSession` ✅ 100%

**Files:** `controllers/match_excel.py`, `controllers/qif_loader.py`  
* ✅ QIF loader returns `list[ITransaction]`.  
* ✅ Excel helpers map groups to protocol transactions; adapters in place.  
* ✅ Existing tests pass.

---

## Phase 7 - Refactor Tabs to Use `DataSession` (Opt-In) ✅ 100%

**Objective:** Allow tabs to optionally use the shared in-memory data without breaking current usage.

### 7.1 Allow tabs to accept an optional session ✅ 100%

**Files:** `merge_tab.py`, `convert_tab.py`, `probe_tab.py`, `app.py`  
* ✅ Tab constructors accept `session: DataSession | None`; store `self._session`.  
* ✅ Tabs reuse cached data when session provided; fallback works for `None`.  
* ✅ `app.py` builds one `DataSession` and passes it to all tabs; tests green.

---

## Phase 8 - `app.py` Shim Removal + Test Migration ✅ 100%

**Objective:** Make `App` only wire the UI and session; remove behavioral shims.

### 8.1 Identify and remove shims from `app.py` ✅ 100%

* ✅ Removed path/emit/payee-filter shims from `app.py`; logic lives in tabs/helpers.  
* ✅ `App.__init__` now constructs session, notebook, tabs only.

### 8.2 Migrate and trim tests in `tests/gui_viewers/test_app.py` ✅ 100%

* ✅ `test_app` trimmed to wiring checks.  
* ✅ ConvertTab-specific tests moved to `test_convert_tab.py`; redundant delegation tests removed.  
* ✅ GUI viewer test suite passes.

---

## Phase 9 - Align `match_excel.py` with `MatchSession` and the New Flow ✅ 100%

**Objective:** Modernize `match_excel.py` to match the protocol-centric `MatchSession` API and be Pylance-clean.

### 9.1 Remove legacy types and maps ✅ 100%

* ✅ Controllers no longer expose `QIFTxnView`/`QIFItemKey`; legacy remains only in legacy helpers/tests.  
* ✅ `MatchSession` exposes protocol-centric fields (`bank_txns`, `excel_txns`, `pairs`, `unmatched_*`; `auto_match`).

### 9.2 Re-implement `build_matched_only_txns(session)` ✅ 100%

* ✅ Implemented in `match_excel.py`, O(n + p), preserves order; typed.

### 9.3 Modernize merge entry points ✅ 100%

* ✅ Added pure helper `run_excel_qif_merge(qif_in, xlsx, encoding, min_score_default, auto_match)` returning `(pairs, unmatched_bank, unmatched_excel)`; keeps I/O-free behavior.  
* ✅ Session construction from paths uses protocol txns and group-to-excel adapters.

### 9.4 QIF writing with `MatchSession` ✅ 100%

* ✅ Tabs use `io_service.write_qif` with protocol txns; matched-only path available via `build_matched_only_txns`.

---

## Phase 10 - Move Transformations Fully "In-Memory" ✅ 100%

**Objective:** Ensure all non-I/O operations are transformations over already-loaded objects from `DataSession`.

### 10.1 Audit tabs for direct file reads ✅ 100%

* ✅ Tabs consult `DataSession` when provided; fall back to local parsing for standalone use/testing.

### 10.2 Centralize write paths ✅ 100%

**Module:** `quicken_helper/controllers/io_service.py`

* ✅ `write_qif`/`write_csv` accept protocol-friendly objects; tabs invoke services rather than raw file writes.

---

## Phase 11 - Richer Error Reporting & UX Hooks ✅ 100%

**Objective:** Provide better visibility when things go wrong.

* ✅ `ParseStats` implemented; `qif_loader.load_transactions_with_stats` used by `DataSession`, `ConvertTab`, and `MergeTab`.  
* ✅ GUI surfaces stats via log panels and info dialogs when warnings occur.  
* ✅ Exceptions logged consistently across tabs/controllers.

---

## Phase 12 - Future Enhancements (Optional / Later) 🟥❌ not started

1. 🟥❌ not started **Cross-reference registry**  
2. 🟥❌ not started **Backgroundable tasks / progress hooks**  
3. 🟥❌ not started **Configurable pipelines**

---

## How Codex Can Use This Roadmap ✅ 90%

1. ✅ Compare current code vs roadmap (Phases 5–11 complete; Phase 12 open).  
2. ✅ Focus follow-ups on optional enhancements (Phase 12) if prioritized.
