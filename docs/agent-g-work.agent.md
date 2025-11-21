# Agent G: Legacy Conversion & Probe Tests

**Scope:** tests/legacy/test_qif_to_csv_unit.py, tests/legacy/test_qfx_to_txn.py, tests/legacy/test_qdx_probe.py  
**Branch:** fix/unit-tests-agent-g  
**Priority:** High (policy blockers, binary/CSV coverage)

---

## Mission

Refactor legacy conversion and probe unit tests to remove all real filesystem I/O while preserving coverage of CSV/QFX/QDX parsing behaviors. Follow unit-test-policy.md and .github/code-change.instructions.md without exception.

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
4. `poetry run pytest tests/legacy/test_qif_to_csv_unit.py tests/legacy/test_qfx_to_txn.py tests/legacy/test_qdx_probe.py -v`

Fix any failures before proceeding.

---

## Tasks

1. `test_qif_to_csv_unit.py`:
   - Remove `tmp_path`; patch `open`/`Path.open` to return `io.StringIO` buffers.
   - Verify CSV content by inspecting captured strings; no actual files.
   - Keep docstrings and AAA structure.
2. `test_qfx_to_txn.py`:
   - Replace file-based XML/QFX fixtures with in-memory strings or `StringIO`.
   - Monkeypatch file reads (`read_text`, `open`) to return fixtures; confirm parsers handle strings.
3. `test_qdx_probe.py`:
   - Substitute all binary file writes/reads with `io.BytesIO`; monkeypatch `Path.write_bytes/read_bytes` accordingly.
   - Preserve entropy/hex-dump assertions using in-memory byte arrays.
4. General:
   - No reliance on filesystem state; deterministic inputs only.
   - Update docs/UNIT_TEST_POLICY_VIOLATIONS.md to mark these files resolved and summarize the mock strategy.

---

## Completion Criteria

- Targeted tests perform zero real file reads/writes.
- Behavior/format assertions remain intact and deterministic.
- All targeted pytest invocations pass.
- Violation document updated with status for all three files.
- Status fields below updated by assignee.

---

## Status Tracking

**Status:** ?? (Not started / In progress / Complete)  
**Last updated:** [fill date]  
**Owner:** [name]  
**Notes/links:** [branch/PR/commits]
