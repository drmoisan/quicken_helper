# quicken_helper code review

## Repository health snapshot
- `poetry run black --check .` ➜ **pass** (`118` files unchanged).
- `poetry run ruff check` ➜ **pass**, but config only enables `E`, `F`, `I` so style coverage is intentionally narrow (`pyproject.toml:24-38`).
- `poetry run pyright` ➜ **fail** with **2676 errors / 4 warnings**. Errors span both runtime modules and tests (sample excerpt shown below).
- `poetry run pytest` ➜ **fail** during collection with 27 import errors because `typing_extensions` is missing.

## Findings and recommendations

### 1. `typing_extensions` dependency missing
- Several modules import `typing_extensions` (`quicken_helper/data_model/interfaces/i_to_dict.py:6`, `i_equatable.py:6`, `i_comparable.py:7`, `legacy/qif_writer.py:37`) but `pyproject.toml` does not list the package anywhere (`pyproject.toml:1-20`).
- Result: `pytest` fails before running a single test and `pyright` stops resolving types for any module that touches these imports (errors reproduced during `poetry run pytest`/`pyright`).
- **Remediation**: either add `typing_extensions` to `[tool.poetry.dependencies]` (required at runtime) or drop the import in favor of the stdlib `typing` equivalents (Python 3.13 already exposes `Protocol`, `TypeAlias`, `Literal`).

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
   - Document the required command sequence (`black`, `ruff`, `pyright`, `pytest`, optional `coverage`) for all future code changes (see `.github/code-transformation-plan.md`).
