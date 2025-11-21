# Agent H: Loader & Utility Test Compliance

**Scope:** tests/controllers/test_qif_loader_protocol.py, tests/utilities/test_core_utilities.py, tests/controllers/test_category_match_session.py  
**Branch:** fix/unit-tests-agent-h  
**Priority:** Medium (quick wins, controller coverage)

---

## Mission

Bring controller and utility tests into full compliance with unit-test-policy.md by eliminating real filesystem usage and tightening mock-based assertions. Adhere strictly to .github/code-change.instructions.md for all code changes.

---

## Core Working Instructions

**MUST READ:**
1. .github/code-change.instructions.md
2. docs/unit-test-policy.md
3. docs/developer-tooling.md
4. docs/UNIT_TEST_POLICY_VIOLATIONS.md (update progress)

**Workflow after any changes:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest tests/controllers/test_qif_loader_protocol.py tests/utilities/test_core_utilities.py tests/controllers/test_category_match_session.py -v`

Do not proceed until all four steps succeed.

---

## Tasks

1. `test_qif_loader_protocol.py`:
   - Remove `tmp_path` usage; supply QIF content via `io.StringIO` or patched `Path.read_text/open`.
   - Assert parsing outcomes without touching disk; ensure deterministic fixtures.
2. `test_core_utilities.py` (open_for_read and related helpers):
   - Replace file creation with `monkeypatch` of `builtins.open` to use `StringIO`.
   - Ensure tests document policy compliance and follow AAA.
3. `test_category_match_session.py` (if any tmp_path remnants remain):
   - Use inert `Path("/mock/file.xlsx")`; keep pandas I/O mocked.
   - Remove any reliance on actual files while preserving assertion intent.
4. General:
   - Confirm every test includes a docstring and clear Arrange-Act-Assert layout.
   - Update docs/UNIT_TEST_POLICY_VIOLATIONS.md to reflect resolved items and method used.

---

## Completion Criteria

- All three files free of real filesystem access and `tmp_path`.
- Tests fully align with unit-test-policy.md and pass under pytest.
- Violation doc updated with status and notes.
- Status fields below filled by assignee.

---

## Status Tracking

**Status:** ?? (Not started / In progress / Complete)  
**Last updated:** [fill date]  
**Owner:** [name]  
**Notes/links:** [branch/PR/commits]
