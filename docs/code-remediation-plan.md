# quicken_helper code remediation plan

## Environment setup (run once per workstation)
1. `poetry install` - creates the managed `.venv` with runtime + dev dependencies.
2. `poetry run pre-commit install` - ensures local git hooks mirror CI once lint/type checks are tightened.
3. Confirm the virtualenv is active for the commands below (`poetry run ...`).

## Required workflow for **every** code change
1. **Read the policy** - skim `docs/unit-test-policy.md` before touching or adding any test to stay aligned on docstring + AAA expectations.
2. **Format** - `poetry run black .` (or `black --check` for validation-only changes).
3. **Lint** - `poetry run ruff check` (initially runs `E`, `F`, `I`; broaden once pyright is green).
4. **Type check** - `poetry run pyright` (must pass with zero errors; only suppress diagnostics we fully understand).
5. **Tests** - `poetry run pytest` and review coverage in `.coverage` (keep the suite deterministic and isolated from external services).
6. **Spot-check logs** - when failures produce `pyright.log`/`pytest.log`, keep them around until the issue is fixed, then delete before committing.
7. **Document** - mention which of the above commands ran (and their outcome) in PR summaries or commit messages for traceability.

## Backlog reduction plan

### Phase 0 - unblock imports ✅
- Replace `typing_extensions` usages with stdlib `typing` (`Protocol`, `TypeAlias`, `Literal`) in:
  - `quicken_helper/data_model/interfaces/i_to_dict.py`
  - `quicken_helper/data_model/interfaces/i_equatable.py`
  - `quicken_helper/data_model/interfaces/i_comparable.py`
  - `quicken_helper/legacy/qif_writer.py`
- Alternatively, add `typing_extensions = "^4.12"` under `[tool.poetry.dependencies]` if backward compatibility is required.
- Re-run `poetry lock` and `poetry install`, then `poetry run pytest` to confirm import errors disappear.

### Phase 0b - protocol mix-in order ✅
- `typing.Protocol` is stricter about MRO than `typing_extensions.Protocol`. Any interface inheriting multiple Protocols must list `Protocol` last (or omit it if every other base already inherits from Protocol).
- Files touched: `i_account.py`, `i_category.py`, `i_header.py`, `i_quicken_file.py`, `i_security.py`, `i_split.py`, `i_tag.py`, `i_transaction.py`.
- Verified via `poetry run pytest` that the MRO error is resolved.

### Phase 0c - restore helper exports ✅
- `tests/controllers/test_match_helpers.py` expects `_candidate_cost` and `_flatten_qif_txns` to exist in `quicken_helper.controllers.match_helpers`.
- Helpers reintroduced (or shimmed) so the controller module exports the tested functions. `pytest tests/controllers/test_match_helpers.py` now passes.

### Phase 0d - declare `pyparsing` dependency ✅
- `quicken_helper/data_model/qif_parsers_emitters/qif_file_parser_emitter.py` imports `pyparsing`, so it is now listed in `pyproject.toml`.
- After `poetry lock` / `poetry install`, the QIF loader tests import cleanly.

### Phase 0e - reintroduce `convert_value` shim ✅
- `tests/controllers/test_match_session*.py` expect `convert_value` to live on `quicken_helper.controllers.match_session`.
- Added a module-level alias that forwards to the canonical helper so the tests can monkeypatch it. The controller suite passes again.

### Phase 1 - tame pandas/Excel entry points ✅
- Shared helper `quicken_helper/utilities/excel_io.read_excel_df` centralizes all pandas access, keeps monkeypatched tests working, and is used by `controllers.match_excel` and `controllers.category_match_session`.
- Regression suites (`tests/controllers/test_match_excel.py`, `tests/controllers/test_category_match_session.py`) cover the new helper paths.
- GUI layers rely on those controllers for Excel ingestion, so no direct pandas usage remains.

### Phase 2 - strengthen automation 

- Wire `black`, `ruff`, `pyright`, and `pytest` into a .vscode/tasks.json file
- Consider adding `coverage.xml` generation plus upload to Codecov (or similar) to enforce minimum coverage thresholds.

### Phase 3 - finish protocol/data-model typing _(in progress)_

#### Phase 3a - dataclasses

- ✅ Dataclass sentinels fixed in `q_transaction.py`; defaults now use `field(default_factory=...)`.
- ✅ `QuickenFile.sections` now initializes to `QuickenSections.NONE` and `emit_transactions` no longer uses dataclasses `Field`.

#### Phase 3b - data-model packages and protocols typing

- Focus on data-model packages (`quicken_helper/data_model/q_wrapper`, `data_model/interfaces`, `utilities/core_util.py`).
- Ensure every protocol and helper exports concrete `TypedDict`/`Protocol` definitions so controllers no longer return `Any`.
- Remaining: protocol typing/coverage work across the rest of the data-model and utility modules.

#### Phase 3c - unit-testing conversion helpers

- Add unit tests (with policy-compliant docstrings) that cover conversion helpers (`core_util.convert_value`, `utilities.converters_*`).


#### Phase 3d - Ruff rule expansion and compliance

- Expand Ruff rules once pyright is green (add `['B', 'UP', 'S', 'TID', 'TCH']` etc. in `pyproject.toml`).

### Phase 4 - update tests to satisfy strict typing + policy _(blocked until earlier phases are complete)_
- Sweep the `tests/` tree:
  - Add docstrings for every `test_*` (examples: `tests/utilities/test_core_utilities.py`, `tests/utilities/test_from_dict.py`).
  - Annotate fixtures (`monkeypatch: pytest.MonkeyPatch`, `tmp_path: Path`) and stub returns.
  - Introduce typed aliases/protocols for GUI stubs (`_ListboxProtocol`, `_TextProtocol`) in `tests/gui_viewers/test_merge_tab.py`.
- After each module batch, run `poetry run pyright tests/<module>` to keep the workload incremental, followed by the full suite when completed.
- **Temporary deviation**: pyright currently excludes the `tests/` tree entirely to unblock work on the rest of the codebase. Re-enable once the earlier phases are complete.

## Ongoing verification
- Maintain the command cadence (`black` → `ruff` → `pyright` → `pytest`) before **every** commit or pull request.
- Keep a running tally of `pyright` errors; refuse to add new code if it increases the count.
- When touching GUI code, run targeted tests (`pytest tests/gui_viewers/test_merge_tab.py`) in addition to the full suite to keep feedback loops fast.
