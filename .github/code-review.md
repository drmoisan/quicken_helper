# quicken_helper code review

## Repository health snapshot
- `poetry run black --check .` ➜ **pass** (`118` files unchanged).
- `poetry run ruff check` ➜ **pass**, but config only enables `E`, `F`, `I` so style coverage is intentionally narrow (`pyproject.toml:24-38`).
- `poetry run pyright` ➜ **fail** with **2648 errors / 0 warnings** (see `pyright.log`). Runtime modules and tests still spew `Unknown` types from pandas pipelines and untyped fixtures.
- `poetry run pytest` ? **fail** late in execution (see latest run): `tests/controllers/test_match_excel.py` now raises `TypeError` because the new `read_excel_df` helper always passes `sheet_name`, several `q_wrapper` dataclasses start life in invalid states (e.g., `QuickenFile.sections` remains a dataclasses `Field`), and legacy/utilities suites assert behaviours that no longer hold.

## Findings and recommendations

### 1. `typing_extensions` dependency missing (resolved)
- Original state: numerous modules imported `typing_extensions` (`quicken_helper/data_model/interfaces/i_to_dict.py:6`, `i_equatable.py:6`, `i_comparable.py:7`, `legacy/qif_writer.py:37`) without declaring the dependency in `pyproject.toml` (`lines 1-20`), so pytest halted with `ModuleNotFoundError`.
- **Current status**: imports now point at stdlib `typing`, so pytest proceeds to later failures and pyright can evaluate the modules. Keep an eye out for any reintroductions in future files.

### 2. Pandas/Excel entry points rely on `Any`, defeating strict typing
- `CategoryMatchSession.apply_to_excel` calls `pd.read_excel` directly (`quicken_helper/controllers/category_match_session.py:62-73`) and defines inline helpers without annotations (`lines 66-69`), so Pyright reports every variable in the block as `Unknown`.
- Similar issues appear throughout `match_excel.py` (`read_excel_df`, `load_excel_rows`, `_flatten_qif_txns`, etc.) where intermediate values are implicitly typed as `Any`, leading to cascades of `reportUnknown*` diagnostics.
- **Remediation**:
  1. Add typed wrappers that narrow `read_excel` to `pandas.DataFrame` when `sheet_name` is `int | str`, plus explicit return annotations plus casts (e.g., `df: DataFrame = cast(DataFrame, pd.read_excel(...))`).
  2. Annotate nested helpers such as `_map_cell` (return `str`) and `pairs` destructuring loops so Pyright can reason about container types.
  3. Audit other pandas entry points (`gui_viewers/merge_tab.py`, `controllers/qif_loader.py`) to ensure we handle `DataFrame | dict` overloads explicitly and never leak `Any`.

### 3. Tests violate the local unit-test policy
- Policy requires docstrings plus explicit Arrange/Act/Assert sections for every test (`.github/unit-test-policy.md`). Numerous tests lack docstrings entirely (e.g., `tests/utilities/test_core_utilities.py:18-55`) or rely on comments instead of docstrings (`tests/utilities/test_from_dict.py:46-102`).
- Several tests also rely on implicit fixture typing, causing Pyright errors such as `reportUnknownParameterType` for `monkeypatch`/`tmp_path` (`tests/utilities/test_core_utilities.py:23-52`, `tests/controllers/test_category_match_session.py:14-70`).
- **Remediation**: sweep the `tests/` tree to ensure every `def test_*` includes a docstring summarizing intent, uses explicit type annotations for fixtures (`monkeypatch: pytest.MonkeyPatch`), and adds type annotations to helper classes/stubs. Convert repeated inline comments into docstrings per policy.

### 4. Pyright noise from dynamically typed stubs
- Stub factories and monkeypatch helpers are untyped, generating hundreds of partially-unknown return types (example: `tests/controllers/test_category_match_session.py:26-40` fake `fuzzy_autopairs` returns `list[tuple[str, str, float]]` but currently returns raw tuples without annotations, so Pyright treats them as `list[tuple[str, str, Unknown]]`).
- GUI tests create stub widgets without base classes or protocol annotations (`tests/gui_viewers/test_merge_tab.py:34-155`), so members such as `.grid`/`.bind` default to `Unknown`.
- **Remediation**: introduce lightweight `Protocol` definitions for GUI stubs, annotate stub attributes/returns, and type alias frequently used fake payloads (e.g., `Pair = tuple[str, str, float]`). This reduces `Unknown` propagation drastically and makes the 2676-error backlog tractable.

### 5. Formatting/lint guardrails cover only a sliver of issues
- Ruff currently runs in `E`, `F`, `I` mode only (`pyproject.toml:29-40`), so style issues (e.g., complex docstrings containing control characters in `match_excel.py:2-80`, `match_session.py:1-40`) are unchecked.
- Several docstrings contain non-ASCII control characters (`quicken_helper/controllers/match_excel.py:2-15`, `match_session.py:2-31`, `gui_viewers/merge_tab.py:42-70`). Besides readability, these characters can cause rendering glitches in editors and should be normalized to plain ASCII.
- **Remediation**: normalize docstrings, then expand Ruff's `select` list (at least `B`, `UP`, `S`, `TID`, etc.) after the current pyright backlog is under control.

### 6. Dataclass sentinels violate `dataclasses` invariants (resolved)
- Previous behavior: `quicken_helper/data_model/q_wrapper/q_transaction.py:28-61` bound module-level sentinels directly to dataclass fields, so Python 3.13 raised `ValueError: mutable default ... use default_factory` during import.
- **Current status**: sentinels are now annotated as `ClassVar`s and feeders use `field(default_factory=...)`, so imports succeed. Keep the identity-based checks (`is not _MISSING_*`) intact when touching this file.

### 7. `match_helpers` no longer exports tested helpers (resolved)
- Original issue: `tests/controllers/test_match_helpers.py` imported `_candidate_cost` and `_flatten_qif_txns`, but `quicken_helper/controllers/match_helpers.py` had those helpers commented out.
- **Current status**: helpers restored with the original semantics, so the controller tests run again.

### 8. Missing `pyparsing` dependency for QIF parsers (resolved)
- `quicken_helper/data_model/qif_parsers_emitters/qif_file_parser_emitter.py` depends on `pyparsing`. The dependency now exists in `pyproject.toml`, so `tests/controllers/test_qif_loader_protocol.py` imports without `ModuleNotFoundError`.

### 9. `match_excel.load_excel_rows` no longer mock-friendly
- `tests/controllers/test_match_excel.py` monkeypatches `pd.read_excel` with a simple `lambda path: df`. The new `read_excel_df` helper always passes `sheet_name=...`, so the lambda now raises `TypeError: unexpected keyword argument 'sheet_name'`.
- **Remediation**: either update the tests to accept `*_, **__` or adjust `read_excel_df` to default `sheet_name` via `kw.setdefault`. Without this, all `match_excel` tests fail.

### 10. `QuickenFile.sections` initialized to a dataclasses `Field`
- `quicken_helper/data_model/q_wrapper/q_file.QuickenFile` still has `sections: QuickenSections = dataclasses.field(...)` defined at runtime, so an instance exposes the `Field` object rather than a `QuickenSections` value.
- `tests/data_model/q_wrapper/test_qif_file.py::test_constructor_initializes_empty_lists_and_none_section` therefore fails (`Field(...) == Enum`).
- **Remediation**: declare `sections: QuickenSections = field(default=QuickenSections.NONE)` (or `default_factory=lambda: QuickenSections.NONE`) and ensure all dataclass defaults are real runtime values instead of the descriptor objects.

### 9. `MatchSession` no longer exposes `convert_value`
- `tests/controllers/test_match_session*.py` rely on monkeypatching `match_session.convert_value`, but the module no longer defines nor re-exports the helper.
- Result: every `MatchSession` test errors during setup with `AttributeError: module ... has no attribute 'convert_value'`, preventing meaningful coverage of the matching logic.
- **Remediation**: either reintroduce a module-level `convert_value` alias (forwarding to `quicken_helper.utilities.core_util.convert_value`) or update the tests + implementation to inject the dependency differently.

## Remediation plan (initial pass)
1. **Unblock the test/typing pipeline**
   - Replace `typing_extensions` imports with stdlib `typing` equivalents or add the package as a dependency.
   - Run `poetry update` to ensure the dependency is installed in `.venv`.
   - Re-run `pytest` to confirm imports succeed before touching type hints.
2. **Tame pyright at the module level**
   - Start with high-value modules (`controllers/category_match_session.py`, `controllers/match_excel.py`, `gui_viewers/merge_tab.py`) and add explicit type annotations and helper casts for pandas objects.
   - Extract common Excel I/O helpers into a typed utility (e.g., `quicken_helper.utilities.excel_io`) so all pandas entry points share stricter signatures.
3. **Make the tests policy-compliant and typed**
   - Sweep `tests/` to add docstrings, fixture type annotations, and typed stub classes. Prioritize modules called out by Pyright logs (`tests/utilities/test_core_utilities.py`, `tests/controllers/test_category_match_session.py`, GUI tests).
   - While touching tests, verify AAA sections are explicit and convert comment blocks into docstrings.
4. **Iterate on remaining pyright noise**
   - Once the worst offenders are addressed, re-run `pyright` and triage the remaining errors by module group (data model, controllers, GUI, legacy).
   - Track progress in batches (e.g., drive error count to <500, then <100, etc.) to avoid releasing partially typed modules.
5. **Strengthen lint/test automation**
   - After pyright is clean, broaden Ruff rule coverage and wire these commands into CI (GitHub Action already present? verify `.github/workflows`).
   - Document the required command sequence (`black`, `ruff`, `pyright`, `pytest`, optional `coverage`) for all future code changes (see `.github/code-remediation-plan.md`).

