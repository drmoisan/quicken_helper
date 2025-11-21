# quicken_helper code remediation plan ✅ 100%

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

## Backlog reduction plan ✅ 100%

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

### Phase 2 - strengthen automation ✅ 100%

- ✅ VS Code tasks (`.vscode/tasks.json`) now run Black, Ruff, Pyright, Pytest, coverage reports, and Codecov uploads in one click.
- ✅ CI workflow `.github/workflows/ci.yml` runs Black (check), Ruff, Pyright, and Pytest on pushes/PRs to `main` using Poetry-installed deps with caching.

### Phase 3 - finish protocol/data-model typing ✅ 100%

#### Phase 3a - dataclasses ✅ 100%

- ✅ `q_transaction.py` now uses `ClassVar` sentinels plus `field(default_factory=...)` for every mutable slot.
- ✅ `QuickenFile.sections` initializes to `QuickenSections.NONE` and `emit_transactions` no longer references dataclasses `Field`.

#### Phase 3b - data-model packages and protocols typing ✅ 100%

- ✅ Completed typing for data-model packages (`quicken_helper/data_model/q_wrapper`, `data_model/interfaces`, `utilities/core_util.py`) with protocol-safe adapters and helpers.
- ✅ Pyright now passes with zero errors across these modules.

#### Phase 3c - unit-testing conversion helpers ✅ 100%

- ✅ Added comprehensive unit tests (123 tests total) with policy-compliant docstrings that cover conversion helpers:
  - ✅ `tests/utilities/test_converters_scalar.py` (90 tests): covers `to_decimal`, `clean_number_like_string`, `_to_int`, `_to_float`, `_to_bool`, `_to_str`, `to_date`, `to_datetime`, and `default_date`
  - ✅ `tests/utilities/test_converters_collection.py` (33 tests): covers `_to_list`, `_to_set`, `_to_frozenset`, `_to_tuple`, `_to_dict`, and `_to_deque`
- ✅ All tests follow Arrange-Act-Assert pattern with clear docstrings explaining purpose.
- ✅ Tests cover positive flows, negative flows (error cases), and edge cases.
- ✅ All 123 new tests pass successfully.

#### Phase 3d - Ruff rule expansion and compliance ✅ 100%

- ✅ Ruff rules expanded (B, UP, S, TID, TCH) and applied; Black formatting applied.
- ✅ Pyright now green; prior unknown-type/test failures resolved (0 remaining).
- ✅ Full `poetry run pytest` currently passes (417 tests).

### Phase 4 - update tests to satisfy strict typing + policy ✅ 100%

- ✅ Pyright strict runs across the full codebase (including tests) with 0 errors.
- ✅ Full `poetry run pytest` passes (417 tests); no obsolete tests remain.
- ✅ Tests retain docstrings/AAA structure; fixtures and helpers typed as needed.

#### Phase 4a - remove obsolete tests ✅ 100%

- ✅ Audited the `tests/` tree and confirmed no tests target removed functionality; no shims exist solely for obsolete tests.

#### Phase 4b - fix failing tests ✅ 100%

- ✅ No failing tests; current suite green. Command cadence executed (`black`, `ruff`, `pyright`, `pytest`).

#### Phase 4c - clean up test typing ✅ 100%

- ✅ Pyright strict covers tests without suppressions; fixtures and stubs typed.
- ✅ Docstrings present and AAA adhered to across the suite.

## Ongoing verification ✅ 100%

- ✅ Maintain the command cadence (`black` → `ruff` → `pyright` → `pytest`) before every commit or pull request; keep pyright errors at zero and continue running targeted GUI tests as noted.
