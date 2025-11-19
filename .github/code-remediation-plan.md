# quicken_helper code remediation plan

## Environment setup (run once per workstation)
1. `poetry install` — creates the managed `.venv` with runtime + dev dependencies.
2. `poetry run pre-commit install` — ensures local git hooks mirror CI once lint/type checks are tightened.
3. Confirm the virtualenv is active for the commands below (`poetry run ...`).

## Required workflow for **every** code change
1. **Read the policy** — skim `.github/unit-test-policy.md` before touching or adding any test to stay aligned on docstring + AAA expectations.
2. **Format** — `poetry run black .` (or `black --check` for validation-only changes).
3. **Lint** — `poetry run ruff check` (initially runs `E`, `F`, `I`; broaden once pyright is green).
4. **Type check** — `poetry run pyright` (must pass with zero errors; only suppress diagnostics we fully understand).
5. **Tests** — `poetry run pytest` and review coverage in `.coverage` (keep the suite deterministic and isolated from external services).
6. **Spot-check logs** — when failures produce `pyright.log`/`pytest.log`, keep them around until the issue is fixed, then delete before committing.
7. **Document** — mention which of the above commands ran (and their outcome) in PR summaries or commit messages for traceability.

## Backlog reduction plan

### Phase 0 - unblock imports
- Replace `typing_extensions` usages with stdlib `typing` (`Protocol`, `TypeAlias`, `Literal`) in:
  - `quicken_helper/data_model/interfaces/i_to_dict.py`
  - `quicken_helper/data_model/interfaces/i_equatable.py`
  - `quicken_helper/data_model/interfaces/i_comparable.py`
  - `quicken_helper/legacy/qif_writer.py`
- Alternatively, add `typing_extensions = "^4.12"` under `[tool.poetry.dependencies]` if backward compatibility is required.
- Re-run `poetry lock` and `poetry install`, then `poetry run pytest` to confirm import errors disappear.

### Phase 0b - protocol mix-in order
- `typing.Protocol` is stricter about MRO than `typing_extensions.Protocol`. Any interface inheriting multiple Protocols must list `Protocol` last (or omit it if every other base already inherits from Protocol).
- Files touched: `i_account.py`, `i_category.py`, `i_header.py`, `i_quicken_file.py`, `i_security.py`, `i_split.py`, `i_tag.py`, `i_transaction.py`.
- Verify via `poetry run pytest` that `TypeError: Cannot create a consistent method resolution order` is gone once the inheritance order is fixed.

### Phase 0c - restore helper exports
- `tests/controllers/test_match_helpers.py` expects `_candidate_cost` and `_flatten_qif_txns` to exist in `quicken_helper.controllers.match_helpers`.
- Reintroduce these helpers (or provide compatibility shims) so the controller module exports the tested functions. Once restored, rerun `pytest tests/controllers/test_match_helpers.py`.

### Phase 0d - declare `pyparsing` dependency
- `quicken_helper/data_model/qif_parsers_emitters/qif_file_parser_emitter.py` imports `pyparsing`, but the dependency is absent from `pyproject.toml`.
- Add `pyparsing` to `[tool.poetry.dependencies]`, run `poetry lock` / `poetry install`, and rerun `pytest tests/controllers/test_qif_loader_protocol.py`.

### Phase 0e - reintroduce `convert_value` shim
- `tests/controllers/test_match_session*.py` expect `convert_value` to live on `quicken_helper.controllers.match_session`.
- Provide a module-level alias that forwards to the canonical helper (`from quicken_helper.utilities.core_util import convert_value as _convert_value` etc.) so the tests can monkeypatch it.
- After adding the alias, rerun the `tests/controllers/test_match_session*.py` suite to confirm setup fixtures pass.

### Phase 1 - tame pandas/Excel entry points
- Modules: `controllers/category_match_session.py`, `controllers/match_excel.py`, `controllers/qif_loader.py`, `gui_viewers/merge_tab.py`.
- Actions:
  1. Introduce a shared helper (e.g., `utilities/excel_io.py`) with typed wrappers returning `DataFrame`.
  2. Annotate nested helpers (`_map_cell`, `_build_list_column`, `pairs` comprehensions) and avoid implicit tuple destructuring that hides types.
  3. Replace `pd.read_excel` calls with `cast(DataFrame, ...)` after verifying `sheet_name` arguments.
  4. Add regression tests covering edge cases (missing columns, preview toggles) with docstrings and AAA structure.
- Ensure new wrappers remain easy to monkeypatch in tests (e.g., pass `sheet_name` via `kw.setdefault` so a simple lambda can accept the call). Currently `tests/controllers/test_match_excel.py` fails because the stubbed `pd.read_excel` does not accept keyword arguments.
- Validate with `pyright` after each file to prevent regressions.

### Phase 2 — update tests to satisfy strict typing + policy
- Sweep the `tests/` tree:
  - Add docstrings for every `test_*` (examples: `tests/utilities/test_core_utilities.py`, `tests/utilities/test_from_dict.py`).
  - Annotate fixtures (`monkeypatch: pytest.MonkeyPatch`, `tmp_path: Path`) and stub returns.
  - Introduce typed aliases/protocols for GUI stubs (`_ListboxProtocol`, `_TextProtocol`) in `tests/gui_viewers/test_merge_tab.py`.
- After each module batch, run `poetry run pyright tests/<module>` to keep the workload incremental, followed by the full suite when completed.

### Phase 3 - finish protocol/data-model typing
- Focus on data-model packages (`quicken_helper/data_model/q_wrapper`, `data_model/interfaces`, `utilities/core_util.py`).
- Ensure every protocol and helper exports concrete `TypedDict`/`Protocol` definitions so controllers no longer return `Any`.
- Add unit tests (with policy-compliant docstrings) that cover conversion helpers (`core_util.convert_value`, `utilities.converters_*`) to guard future refactors.
- Fix dataclass sentinels that currently break imports: `quicken_helper/data_model/q_wrapper/q_transaction.py` uses module-level `_MISSING_*` helpers as direct defaults. Convert them to `ClassVar`s and switch fields to `field(default_factory=...)` (e.g., `cleared` uses a lambda returning `EnumClearedStatus.UNKNOWN`, `splits` uses `list`). Re-run `poetry run pytest` afterwards to confirm collection succeeds.
- Audit other dataclasses such as `quicken_helper/data_model/q_wrapper/q_file.QuickenFile`; `sections` still holds a `dataclasses.Field` instance instead of `QuickenSections.NONE`. Update defaults to real values and add targeted tests.

### Phase 4 — strengthen automation
- Expand Ruff rules once pyright is green (add `["B", "UP", "S", "TID", "TCH"]` etc. in `pyproject.toml`).
- Wire `black`, `ruff`, `pyright`, and `pytest` into a GitHub Actions workflow under `.github/workflows/ci.yml` (if not already present).
- Consider adding `coverage.xml` generation plus upload to Codecov (or similar) to enforce minimum coverage thresholds.

## Ongoing verification
- Maintain the command cadence (`black` → `ruff` → `pyright` → `pytest`) before **every** commit or pull request.
- Keep a running tally of `pyright` errors; refuse to add new code if it increases the count.
- When touching GUI code, run targeted tests (`pytest tests/gui_viewers/test_merge_tab.py`) in addition to the full suite to keep feedback loops fast.
