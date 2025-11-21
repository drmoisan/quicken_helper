# Agent F: Legacy QIF Writer Cleanup

**Scope:** tests/legacy/test_qif_writer.py, tests/legacy/test_qif_writer_extra.py  
**Branch:** fix/unit-tests-agent-f  
**Priority:** High (policy blockers)

---

## Mission

Eliminate filesystem I/O from the legacy QIF writer unit tests while keeping format and line-ending coverage intact. All changes must strictly follow unit-test-policy.md and the canonical code change rules in .github/code-change.instructions.md.

---

## Core Working Instructions

**MUST READ before coding:**
1. .github/code-change.instructions.md
2. docs/unit-test-policy.md
3. docs/developer-tooling.md
4. docs/UNIT_TEST_POLICY_VIOLATIONS.md (keep status in sync)

**Required workflow after every change:**
1. `poetry run black .`
2. `poetry run ruff check`
3. `poetry run pyright`
4. `poetry run pytest tests/legacy/test_qif_writer*.py -v`

Fix failures before moving on.

---

## Tasks

1. Replace disk writes with in-memory captures:
   - Patch `builtins.open` or `Path.open/write_text/write_bytes` to use `io.StringIO`/`io.BytesIO` so no files are created.
   - Preserve newline behavior (CRLF vs LF) inside captured text; assert against captured buffer content instead of reading files.
2. Remove `tmp_path` and any path existence checks in both target files. Use inert `Path` instances (e.g., `Path("/mock/output.qif")`) where names are needed only for display.
3. Keep assertions focused on formatting and delegation, not filesystem state. Ensure each test has a docstring and follows AAA.
4. Ensure encoding parameters are honored by using mocks that accept `encoding` and `newline` arguments.
5. Update docs/UNIT_TEST_POLICY_VIOLATIONS.md to mark these files resolved and note the mock-based strategy used.

---

## Completion Criteria

- No targeted test writes to disk or relies on `tmp_path`.
- Format expectations verified via captured buffers.
- Tests comply with unit-test-policy.md and pass under pytest.
- Violation document updated with new status and rationale.
- Status fields below filled in.

---

## Status Tracking

**Status:** ?? (Not started / In progress / Complete)  
**Last updated:** [fill date]  
**Owner:** [name]  
**Notes/links:** [branch/PR/commits]
