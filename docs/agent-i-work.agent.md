# Agent I: GUI Tab Test Compliance

**Scope:** tests/gui_viewers/test_merge_tab.py, tests/gui_viewers/test_category_popout.py  
**Branch:** fix/unit-tests-agent-i  
**Priority:** High (GUI coverage and policy blockers)

---

## Mission

Refactor GUI tab tests to remove all filesystem interactions (including `tmp_path`) while keeping coverage of MergeTab and CategoryPopout behaviors. Strictly follow unit-test-policy.md and .github/code-change.instructions.md for every change.

---

## Core Working Instructions

**MUST READ:**
1. .github/code-change.instructions.md
2. docs/unit-test-policy.md
3. docs/developer-tooling.md
4. docs/UNIT_TEST_POLICY_VIOLATIONS.md

**Workflow after code changes:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest tests/gui_viewers/test_merge_tab.py tests/gui_viewers/test_category_popout.py -v`

Iterate until all steps pass.

---

## Tasks

1. `test_merge_tab.py`:
   - Remove `tmp_path` usage; use inert Paths (e.g., `Path("/mock/input.qif")`) and mock all file reads/writes (pandas, io_service, Path methods).
   - Ensure GUI components remain stubbed/mocked so tests are deterministic and fast.
   - Keep docstrings and explicit AAA structure; avoid hidden fixtures that obscure intent.
2. `test_category_popout.py`:
   - Ensure the earlier mock-path fix is complete; no actual files or `write_text` calls.
   - Maintain focus on category editing behavior only.
3. General:
   - No real filesystem interaction; all I/O mocked or in-memory.
   - Update docs/UNIT_TEST_POLICY_VIOLATIONS.md to mark these files resolved and note mock strategy.

---

## Completion Criteria

- Zero filesystem writes/reads in targeted tests.
- Tests comply with unit-test-policy.md and pass under pytest.
- Violation doc updated with new status and rationale.
- Status tracking fields completed by assignee.

---

## Status Tracking

**Status:** ?? (Not started / In progress / Complete)  
**Last updated:** [fill date]  
**Owner:** [name]  
**Notes/links:** [branch/PR/commits]
