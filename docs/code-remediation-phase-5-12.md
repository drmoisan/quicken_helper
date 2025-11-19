Here you go—same roadmap, just renumbered so it starts at **Phase 5** (and all internal references adjusted).

---

## High-Level Targets

Across all phases, the goals are:

- **Load once, work in memory, write once**

   * Consolidate all loading/parsing to a small set of loaders.
   * All transforms operate on `ITransaction` / `ExcelTransaction` instances, not on raw rows/dicts.
- **App is just wiring; tabs own behavior**

   * Remove `app.py` shims (paths, emit vars, helper methods).
   * Migrate shim-driven tests into tab-specific tests.
- **Match pipeline is protocol-centric and type-safe**

   * `MatchSession` and `match_excel.py` use shared protocols and no legacy `QIFTxnView` / “groups in the session”.
- **Logging is rich and consistent**

   * Standard logging across tabs + controllers, good diagnostics for failures.

Codex can treat each phase as a separate PR or commit chain.

---

## Phase 5 — Logging + Diagnostics Foundation

**Objective:** Add consistent, low-risk logging to the GUI tabs and controllers.

### 5.1 Add module-level loggers

**Files:**

* `quicken_helper/gui_viewers/convert_tab.py`
* `quicken_helper/gui_viewers/probe_tab.py`
* (Verify `merge_tab.py` already has a logger; if not, add it there too.)
* Optionally: `quicken_helper/controllers/match_excel.py`, `match_session.py`, loaders/writers.

**Tasks:**

1. At top of each module:

   ```python
   import logging
   log = logging.getLogger(__name__)
   ```
2. Wrap critical operations with `log.debug` / `log.info`, e.g.:

   * Input/output paths selected.
   * Emit mode (“qif”, “csv”, etc).
   * Start/finish of long operations (parse, match, write).
3. On exception paths where you currently show a `messagebox` or similar:

   * Log with `log.exception("...")` before surfacing UI error messages.

**Invariants:**

* No behavior change; tests should remain green.
* No new `Any` leaks; log calls should not force type loosening.

---

## Phase 6 — Centralized Loading & In-Memory “DataSession”

**Objective:** Stop re-loading files in multiple places; create a shared in-memory model.

### 6.1 Introduce a `DataSession` (or similarly named) controller

**New module:**

* `quicken_helper/controllers/data_session.py`

**Responsibilities:**

* **Fields (proposed):**

  ```python
  from pathlib import Path
  from typing import Sequence
  from quicken_helper.data_model.interfaces import ITransaction
  from quicken_helper.data_model.excel_types import ExcelTransaction  # adjust to actual type name

  class DataSession:
      bank_path: Path | None
      bank_txns: list[ITransaction]

      excel_path: Path | None
      excel_txns: list[ExcelTransaction]

      # Optional: other sources (probes, secondary qif, etc.)
  ```

* **Methods:**

  * `load_bank_qif(path: Path, encoding: str = "utf-8") -> None`

    * Use your canonical QIF parser to produce `list[ITransaction]`.
  * `load_excel(path: Path) -> None`

    * Use `match_excel.load_excel_rows` + adapters to get `list[ExcelTransaction]`.
  * Optionally: `clear()` to reset.

**Constraints:**

* `DataSession` **does not** know about GUI or tabs.
* All types must be concrete and Pylance-clean.

### 6.2 Convert existing loaders to feed `DataSession`

**Files:**

* `match_excel.py` (Excel side)
* QIF loader(s) (wherever your canonical QIF→`ITransaction` lives; e.g. `q_wrapper/q_file.py` and helpers)

**Tasks:**

1. Standardize the QIF loader to produce `list[ITransaction]` rather than ad-hoc dicts.
2. In `match_excel.py`, ensure:

   * `load_excel_rows` + `group_excel_rows` remain the low-level helpers.
   * A new helper `excel_groups_to_txns(groups) -> list[ExcelTransaction]` (or equivalent) converts groups to protocol objects using your existing adapter (e.g. `map_group_to_excel_txn`.

**Invariants:**

* Existing tests that rely on `load_excel_rows` / `group_excel_rows` should still pass.
* No tab uses `DataSession` yet; this phase is additive.

---

## Phase 7 — Refactor Tabs to Use `DataSession` (Opt-In)

**Objective:** Let tabs *optionally* use the shared in-memory data, without breaking current usage.

### 7.1 Allow `MergeTab` / `ConvertTab` / `ProbeTab` to accept an optional session

**Files:**

* `gui_viewers/merge_tab.py`
* `gui_viewers/convert_tab.py`
* `gui_viewers/probe_tab.py`
* `gui_viewers/app.py` (to pass the session in when creating tabs)

**Tasks:**

1. Update tab constructors to accept an optional `session: DataSession | None = None`.

   * Store it as `self._session`.
2. When files are chosen via the UI in each tab:

   * Instead of re-parsing inside the tab, call `self._session.load_...` when `self._session` is not `None`.
   * Keep the current, direct parsing logic as a fallback when no session is provided (for backward compatibility).

**Example (pattern, not code):**

* In `ConvertTab.run()`:

  * If `self._session` and `self._session.bank_path == in_path` and `self._session.bank_txns` already loaded, reuse those.
  * Otherwise, load via the canonical loader into session, then use `session.bank_txns`.

**Invariants:**

* `app.py` should now build a single `DataSession` and pass it to each tab.
* All tests for tabs should still pass (since they can instantiate tabs with `session=None` if needed).

---

## Phase 8 — `app.py` Shim Removal + Test Migration

**Objective:** Make `App` only wire the UI and session; remove behavioral shims.

### 8.1 Identify and remove shims from `app.py`

**Likely shims:**

* Public attributes like `app.in_path`, `app.out_path`, `app.emit_var`.
* Methods like `_update_output_extension`, `_parse_payee_filters`, `_run`, `_m_normalize_categories`, etc.

**Tasks:**

1. Move shim logic into the *appropriate tab*:

   * Path / extension logic → `ConvertTab` methods.
   * Payee filter parsing → `ConvertTab` or a shared helper module.
   * Normalize categories delegation → `MergeTab` (already has coverage elsewhere).
2. In `App.__init__`:

   * Only create `DataSession`, `Notebook`, and tab instances.
   * Stop exposing shim attributes/methods on `App`.

**Invariants:**

* Running the app still works (tabs now own behavior).
* No direct references to these shims in the codebase (search/shoot).

### 8.2 Migrate and trim tests in `tests/gui_viewers/test_app.py`

**Actions (per earlier breakdown):**

1. **Keep (but trim)**:

   * `test_app_init_wires_tabs_and_shims` → rename/modify to `test_app_init_builds_tabs`.
   * New assertions:

     * App builds root window / notebook.
     * Notebook has 3 tab frames (Merge/Convert/Probe) or however many currently.
   * **Remove** assertions about shims (no `app.in_path`, etc.).

2. **Migrate to `test_convert_tab.py`:**

   * From `test_app.py`, move tests that really belong to `ConvertTab`:

     * `test_update_output_extension_blank_out_uses_in_path`
     * `test_update_output_extension_switches_extension`
     * `test_parse_payee_filters_parses_lines_and_commas`
     * `test_run_missing_input_shows_error`
     * `test_run_missing_output_shows_error`
     * `test_run_decline_overwrite_does_not_write`
     * `test_run_writes_csv_windows_profile`
   * Rewrite them so they instantiate `ConvertTab` directly, using dummy Tk root and test doubles for messageboxes / file I/O.

3. **Eliminate redundant tests:**

   * `test_m_normalize_categories_delegates_to_merge_tab` — covered by `test_merge_tab` tests.
   * Any app-only QIF-write test that is now redundant with QIF writer + `MergeTab` tests.

**Invariants:**

* `pytest tests/gui_viewers` remains green.
* No tests reference `App` shims anymore.

---

## Phase 9 — Align `match_excel.py` with `MatchSession` and the New Flow

**Objective:** Modernize `match_excel.py` to match the protocol-centric `MatchSession` API and be Pylance-clean.

### 9.1 Remove legacy types and maps

**Files:**

* `controllers/match_excel.py`
* `controllers/match_session.py` (for imports and API consistency)

**Tasks:**

1. Delete or stop importing:

   * `QIFTxnView`
   * `QIFItemKey`
   * Any `session.excel_groups` or `session.qif_to_excel_group` references.
2. Verify `MatchSession` exposes:

   * `bank_txns: list[ITransaction]`
   * `excel_txns: list[ITransaction] | list[ExcelTransaction]`
   * `pairs: list[tuple[ITransaction, ITransaction]]`
   * `unmatched_bank`, `unmatched_excel`
   * Optional: `auto_match()` or similar.

### 9.2 Re-implement `build_matched_only_txns(session)` with new API

**Target signature:**

```python
from quicken_helper.data_model.interfaces import ITransaction
from quicken_helper.controllers.match_session import MatchSession

def build_matched_only_txns(session: MatchSession) -> list[ITransaction]:
    """Return bank-side transactions that participate in session.pairs."""
```

**Implementation outline:**

* Build a `set` of bank txn identities or indices from `session.pairs`.

  * To avoid O(n²), make a dict: `id(txn) -> index` for `session.bank_txns`.
* Return a list of `session.bank_txns[i]` for all matched indices in sorted order.

**Invariants:**

* No mutation of `session`.
* Type annotations fully concrete, Pylance-clean.

### 9.3 Modernize `run_excel_qif_merge(...)`

**Target behavior:** Accept QIF + Excel paths, return matched + unmatched lists of protocol transactions.

**Proposed signature:**

```python
from pathlib import Path
from typing import Tuple
from quicken_helper.data_model.interfaces import ITransaction

def run_excel_qif_merge(
    qif_in: Path,
    xlsx: Path,
    *,
    encoding: str = "utf-8",
) -> tuple[list[tuple[ITransaction, ITransaction]], list[ITransaction], list[ITransaction]]:
    """Parse/convert→match and return (pairs, unmatched_bank, unmatched_excel)."""
```

**Tasks:**

1. Load QIF as `bank_txns: list[ITransaction]` via canonical loader.
2. Load Excel as:

   * `rows = load_excel_rows(xlsx)`
   * `groups = group_excel_rows(rows)`
   * `excel_txns = [map_group_to_excel_txn(g) for g in groups]`
3. Build a `MatchSession(bank_txns, excel_txns)` and run matching (e.g. `session.auto_match()`).
4. Return `(session.pairs, session.unmatched_bank, session.unmatched_excel)`.

**Important:** Do **not** embed “apply updates and write QIF” inside this function anymore; keep it as pure matching and return data.

### 9.4 Decide how writing QIF uses `MatchSession` (and update `MergeTab`)

**Goal:** Have a single, type-safe path from `MatchSession` → QIF writer.

**Options:**

**Option A: Writer accepts `ITransaction` directly**

* Implement (or adjust) a QIF writer that takes `list[ITransaction]`.
* In `MergeTab`:

  * If `only_matched`:

    ```python
    bank_txns = build_matched_only_txns(session)
    ```
  * Else:

    ```python
    bank_txns = session.bank_txns
    ```
  * Then:

    ```python
    write_qif(bank_txns, out_path, encoding=...)
    ```

**Option B: Convert to legacy dicts right before writing**

* Add `to_qif_dict(txn: ITransaction) -> dict[str, str | Decimal | date]` helper in a QIF-specific module.
* Keep everything in protocols until the final conversion.

**Invariants:**

* `MergeTab` no longer expects `session.txns` or `session.apply_updates()` if these no longer exist on `MatchSession`.
* All match/QIF tests pass and Pylance is satisfied.

---

## Phase 10 — Move Transformations Fully “In-Memory”

**Objective:** Ensure all non-I/O operations are transformations over already-loaded objects from `DataSession`.

### 10.1 Audit `MergeTab`, `ConvertTab`, `ProbeTab` for direct file reads

For each tab:

1. **Replace:**

   * Ad-hoc file parsing with `DataSession` access:

     * `self._session.bank_txns`
     * `self._session.excel_txns`
2. **Ensure:**

   * If a tab must support being used without a `DataSession` (e.g. tests), it falls back to the old behavior or gets a minimal `DataSession` created in the test.

### 10.2 Centralize write paths

**New or existing module:**

* `quicken_helper/controllers/io_service.py` (name flexible)

**Responsibilities:**

* `write_qif(txns: Sequence[ITransaction], path: Path, encoding: str = "utf-8")`
* `write_csv(txns: Sequence[ITransaction], path: Path, dialect/options)` — or more narrow, depending on existing emit options.

**Invariants:**

* Tabs call these services instead of writing directly.
* Options are passed explicitly; no hidden globals.

---

## Phase 11 — Richer Error Reporting & UX Hooks

**Objective:** Better visibility when things go wrong.

**Tasks:**

1. **Parse stats:** where feasible, record:

   * Number of lines read.
   * Number of transactions parsed / skipped.
   * Sample of errors (e.g. 3 representative bad lines).
2. **Surfacing:**

   * Expose a structured error object or text summary from controllers to tabs.
   * Tabs show UI messages while logs capture full details.

**Invariants:**

* No controller depends on Tkinter; they return plain data / exceptions.
* Tabs translate that into messageboxes and/or dedicated “log” panes.

---

## Phase 12 — Future Enhancements (Optional / Later)

These came up in earlier conversations and can be done after the core refactor is stable:

1. **Cross-reference registry**

   * Build a module that can map transactions across multiple bank/QIF sources using keys and heuristics.
2. **Backgroundable tasks / progress hooks**

   * Structure long-running operations so they can be wrapped in progress reporting later (even if still blocking now).
3. **Configurable pipelines**

   * Allow named “recipes” for conversion and merge steps that users can select.

---

## How Codex Can Use This Roadmap

When you feed this to Codex in VSCode, you can ask it to:

1. **Compare current code vs roadmap**:

   * “Show me where **Phase 8.1** is already done and where it’s not.”
2. **Implement phase by phase**:

   * “Implement **Phase 7.1** exactly as described.”
   * “Refactor `match_excel.py` per **Phase 9** and add tests ensuring `build_matched_only_txns` works.”

This should now slot cleanly after your existing “Phase 1–4” remediation roadmap.
