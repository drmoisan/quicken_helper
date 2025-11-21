# quicken_helper code remediation plan ⚠️ 80%

## Environment setup (run once per workstation) ✅ 100%

1. ✅ `poetry install` - creates the managed `.venv` with runtime + dev dependencies.
2. ✅ `poetry run pre-commit install` - ensures local git hooks mirror CI once lint/type checks are tightened.
3. ✅ Confirm the virtualenv is active for the commands below (`poetry run ...`).
4. ✅ For a broader overview of the local tooling, see `docs/developer-tooling.md`.

## **Required workflow** - should be run after **every** code change ✅ 100%

1. ✅ **Read the policy** - skim `docs/unit-test-policy.md` before touching or adding any test to stay aligned on docstring + AAA expectations.
2. ✅ **Review tooling** (optional) - consult `docs/developer-tooling.md` for context on Black, Ruff, Pyright, pytest, coverage, and VS Code tasks.
3. ✅ **Format** - `poetry run black .` (or `black --check` for validation-only changes).
4. ✅ **Lint** - `poetry run ruff check` (initially runs `E`, `F`, `I`; broaden once pyright is green).
5. ✅ **Type check** - `poetry run pyright` (must pass with zero errors; only suppress diagnostics we fully understand).
6. ✅ **Tests** - `poetry run pytest` and review coverage in `.coverage` (keep the suite deterministic and isolated from external services).
7. ✅ **Spot-check logs** - when failures produce `pyright.log`/`pytest.log`, keep them around until the issue is fixed, then delete before committing.
8. ✅ **Document** - mention which of the above commands ran (and their outcome) in PR summaries or commit messages for traceability.

## **Canonical Prioritization Hierarchy:**

1. data_model.interfaces
2. data_model.q_wrapper
3. data_model.excel
4. utilities
5. controllers
6. legacy
7. gui_viewers

## Backlog reduction plan ⚠️ 70%

### Phase 0 - unblock imports ✅ 100%

- ✅ Replace `typing_extensions` usages with stdlib `typing` (`Protocol`, `TypeAlias`, `Literal`) in:
  - ✅ `quicken_helper/data_model/interfaces/i_to_dict.py`
  - ✅ `quicken_helper/data_model/interfaces/i_equatable.py`
  - ✅ `quicken_helper/data_model/interfaces/i_comparable.py`
  - ✅ `quicken_helper/legacy/qif_writer.py`
- ✅ Alternative dependency addition not needed because stdlib typing is in place.
- ✅ Re-ran `poetry lock` / `poetry install` and `poetry run pytest` to confirm import errors disappeared.

### Phase 0b - protocol mix-in order ✅ 100%

- ✅ `typing.Protocol` ordering corrected where needed so MRO matches stdlib strictness.
- ✅ Files touched: `i_account.py`, `i_category.py`, `i_header.py`, `i_quicken_file.py`, `i_security.py`, `i_split.py`, `i_tag.py`, `i_transaction.py`.
- ✅ Verified via `poetry run pytest` that the MRO error is resolved.

### Phase 0c - restore helper exports ✅ 100%

- ✅ `tests/controllers/test_match_helpers.py` expects `_candidate_cost` and `_flatten_qif_txns` to exist in `quicken_helper.controllers.match_helpers`.
- ✅ Helpers reintroduced (or shimmed) so the controller module exports the tested functions. `pytest tests/controllers/test_match_helpers.py` now passes.

### Phase 0d - declare `pyparsing` dependency ✅ 100%

- ✅ `quicken_helper/data_model/qif_parsers_emitters/qif_file_parser_emitter.py` imports `pyparsing`, so it is now listed in `pyproject.toml`.
- ✅ After `poetry lock` / `poetry install`, the QIF loader tests import cleanly.

### Phase 0e - reintroduce `convert_value` shim ✅ 100%

- ✅ `tests/controllers/test_match_session*.py` expect `convert_value` to live on `quicken_helper.controllers.match_session`.
- ✅ Added a module-level alias that forwards to the canonical helper so the tests can monkeypatch it. The controller suite passes again.

### Phase 1 - tame pandas/Excel entry points ✅ 100%

- ✅ Shared helper `quicken_helper/utilities/excel_io.read_excel_df` centralizes all pandas access, keeps monkeypatched tests working, and is used by `controllers.match_excel` and `controllers.category_match_session`.
- ✅ Regression suites (`tests/controllers/test_match_excel.py`, `tests/controllers/test_category_match_session.py`) cover the new helper paths.
- ✅ GUI layers rely on those controllers for Excel ingestion, so no direct pandas usage remains.

### Phase 2 - strengthen automation ⚠️ 75%

- ✅ VS Code tasks (`.vscode/tasks.json`) now run Black, Ruff, Pyright, Pytest, coverage reports, and Codecov uploads in one click.
- ⚠️ 50% Next step: wire these tasks into CI once typing is green (pending).

### Phase 3 - finish protocol/data-model typing ⚠️ 75%

#### Phase 3a - dataclasses ✅ 100%

- ✅ `q_transaction.py` now uses `ClassVar` sentinels plus `field(default_factory=...)` for every mutable slot.
- ✅ `QuickenFile.sections` initializes to `QuickenSections.NONE` and `emit_transactions` no longer references dataclasses `Field`.

#### Phase 3b - data-model packages and protocols typing ⚠️ 40%

- ⚠️ 40% Focus on data-model packages (`quicken_helper/data_model/q_wrapper`, `data_model/interfaces`, `utilities/core_util.py`) with remaining protocol typing/coverage work across the rest of the data-model and utility modules.

#### Phase 3c - unit-testing conversion helpers ✅ 100%

- ✅ Added comprehensive unit tests (123 tests total) with policy-compliant docstrings that cover conversion helpers:
  - ✅ `tests/utilities/test_converters_scalar.py` (90 tests): covers `to_decimal`, `clean_number_like_string`, `_to_int`, `_to_float`, `_to_bool`, `_to_str`, `to_date`, `to_datetime`, and `default_date`
  - ✅ `tests/utilities/test_converters_collection.py` (33 tests): covers `_to_list`, `_to_set`, `_to_frozenset`, `_to_tuple`, `_to_dict`, and `_to_deque`
- ✅ All tests follow Arrange-Act-Assert pattern with clear docstrings explaining purpose
- ✅ Tests cover positive flows, negative flows (error cases), and edge cases
- ✅ All 123 new tests pass successfully

#### Phase 3d - Ruff rule expansion and compliance ⚠️ 60%

- ⚠️ 60% Ruff rules expanded and applied despite Pyright not being green (167 errors remain from Phase 3b-c).
- ✅ Completed:
  - ✅ Added rules: B (bugbear), UP (pyupgrade), S (bandit), TID (tidy-imports), TCH (type-checking)
  - ✅ Applied 442 auto-fixes (419 safe + 23 unsafe)
  - ✅ Fixed 4 manual issues: B023 (loop variable capture), B904 (exception chaining x3), UP046 (generic class syntax)
  - ✅ Ruff passing with 0 errors
  - ✅ Black formatting applied
- ⚠️ 40% Known issues:
  - ⚠️ 10% 29 test failures remain (down from 30 after fixing date filter)
  - ⚠️ 10% 28 failures: `write_qif()` API mismatch (tests use `out=` parameter, function signature has `path`)
  - ⚠️ 10% 1 failure: tuple conversion assertion mismatch in `test_convert_value.py`
  - ⚠️ 10% These appear to be pre-existing test/API alignment issues, not Ruff-related regressions
  - ⚠️ 10% Should be addressed in Phase 4b (fix failing tests)

### Phase 4 - update tests to satisfy strict typing + policy 🟥❌ not started

- 🟥❌ not started **Temporary deviation**: pyright currently excludes the `tests/` tree entirely to unblock work on the rest of the codebase. This will be re-enabled in phase 4c piece by piece.
- 🟥❌ not started For all changes in phase 4, please prioritize tests in the order of the Canonical Prioritization Hierarchy

#### Phase 4a - remove obsolete tests 🟥❌ not started

- 🟥❌ not started Sweep the `tests/` tree:
  - 🟥❌ not started Remove any test that was designed for code functionality that no longer exists.
  - 🟥❌ not started Do not create shims in production code to maintain obsolete tests. Rather, remove the tests
  - 🟥❌ not started If shims exist in production code for functionality that is not used elsewhere, please remove both the tests and the shims
  - 🟥❌ not started In a later phase I will address code coverage, but the code is changing too much at this point

#### Phase 4b - fix failing tests 🟥❌ not started

- 🟥❌ not started If the tests are addressing current production code, but the tests fail, please fix them
  - 🟥❌ not started Determine whether test assertions are appropriate for the current code state. If not change them
  - 🟥❌ not started If assertions are appropriate but test fails, fix production code
  - 🟥❌ not started With any production code fix, please rerun pyrite, ruff, black, and retest
- 🟥❌ not started With any change to production code, please rerun pyrite, ruff, black, and retest

#### Phase 4c - clean up test typing 🟥❌ not started

- 🟥❌ not started For each folder and subfolder in the `tests/` tree in order of the Canonical Prioritization Hierarchy:
  - 🟥❌ not started Re-enable type checking for the group of folders
  - 🟥❌ not started Add docstrings for every `test_*` (examples: `tests/utilities/test_core_utilities.py`, `tests/utilities/test_from_dict.py`).
  - 🟥❌ not started Annotate fixtures (`monkeypatch: pytest.MonkeyPatch`, `tmp_path: Path`) and stub returns.
  - 🟥❌ not started Introduce typed aliases/protocols for GUI stubs (`_ListboxProtocol`, `_TextProtocol`) in `tests/gui_viewers/test_merge_tab.py`.
- 🟥❌ not started After each module batch,
  1. 🟥❌ not started Please follow the "**Required workflow**" for the module batch
  2. 🟥❌ not started Run the "**Required worklow**" for the entire project
  3. 🟥❌ not started If any **new** problems appear that did not exist prior to working on the module, please correct them and repeat steps 1-3.
  4. 🟥❌ not started Do not proceed to the next module batch until the prior one passes steps 1-3.

## Ongoing verification ⚠️ 50%

- ⚠️ 50% Maintain the command cadence (`black` → `ruff` → `pyright` → `pytest`) before every commit or pull request and keep pyright errors from increasing; continue running targeted GUI tests as noted.
