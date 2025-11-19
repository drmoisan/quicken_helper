# Agent Work Allocation (Phases 5-12)

**Purpose:** Track parallel agent work for Phase 5-12 remediation roadmap.

**Last updated:** 2025-01-19

---

## Status Dashboard

| Agent | Phases | Status | Branch | Blocked By | Last Updated |
|-------|--------|--------|--------|------------|--------------|
| **A** | 5, 6.2 | 🟡 Ready | `refactor/logging-foundation` | None | 2025-01-19 |
| **B** | 7.1 | 🟡 Waiting | `refactor/tab-session-opt-in` | Agent A | 2025-01-19 |
| **C** | 9 (all) | 🟢 Ready | `refactor/match-pipeline` | None | 2025-01-19 |
| **D** | 8, 10, 11 | ⏸️ Blocked | `refactor/app-cleanup` | A, B, C | 2025-01-19 |

**Legend:**
- 🟢 Ready to Start (no blockers)
- 🟡 Waiting (dependencies not met)
- 🔵 In Progress
- ✅ Complete
- ⏸️ Blocked (cannot start yet)

---

## Detailed Agent Work Documents

Each agent has a comprehensive work document with:
- Complete task breakdown
- API contracts and promises
- Testing strategy
- Completion criteria
- Quick reference commands

**Agent Work Files:**
- **[Agent A: Foundation & Infrastructure](agent-a-work.agent.md)** - Phases 5, 6.2
- **[Agent B: Tab Refactoring](agent-b-work.agent.md)** - Phase 7.1
- **[Agent C: Match Pipeline Modernization](agent-c-work.agent.md)** - Phase 9 (all)
- **[Agent D: Cleanup & Polish](agent-d-work.agent.md)** - Phases 8, 10, 11

---

## Work Waves & Sequencing

### Wave 1: Parallel Foundation (Start Immediately)

**Agent A + Agent C can work in parallel:**
- Different file sets, minimal conflicts
- Agent A: Logging + DataSession
- Agent C: Match pipeline modernization

### Wave 2: Tab Refactoring

**Agent B starts after Agent A completes:**
- Depends on stable DataSession API
- Can overlap with Agent C if coordinated

### Wave 3: Cleanup

**Agent D starts after all others complete:**
- Sequential cleanup phase
- Depends on all refactoring being done

---

## Integration Sequence & Merge Order

```
┌─────────────────────────────────────────────┐
│ Wave 1 (Parallel)                           │
├─────────────────────────────────────────────┤
│ Agent A: Logging + DataSession              │
│ Agent C: Match pipeline                     │
└─────────────────────────────────────────────┘
              ↓
         (A merges first)
              ↓
┌─────────────────────────────────────────────┐
│ Wave 2                                       │
├─────────────────────────────────────────────┤
│ Agent B: Tab refactoring                    │
│         (consumes A's DataSession)          │
│         (eventually uses C's match API)     │
└─────────────────────────────────────────────┘
              ↓
         (C merges)
              ↓
         (B merges)
              ↓
┌─────────────────────────────────────────────┐
│ Wave 3                                       │
├─────────────────────────────────────────────┤
│ Agent D: App cleanup, I/O, error reporting  │
└─────────────────────────────────────────────┘
              ↓
      Phases 5-11 Complete! 🎉
```

**Recommended merge order:**
1. Agent A → master (establishes foundation)
2. Agent C → master (match pipeline ready)
3. Agent B → master (tabs integrate both A and C)
4. Agent D → master (final cleanup)

---

## API Contracts Between Agents

### Agent A Provides (for Agent B):

```python
# quicken_helper/controllers/data_session.py
@dataclass
class DataSession:
    qif_path: Path | None
    qif_txns: list[ITransaction]
    excel_path: Path | None
    excel_txns: list[ExcelTransaction]
    
    def load_qif(self, path: Path, *, encoding: str = "utf-8") -> list[ITransaction]
    def load_excel(self, path: Path) -> list[ExcelTransaction]
```

### Agent C Provides (for Agent B):

```python
# quicken_helper/controllers/match_excel.py
def build_matched_only_txns(session: MatchSession) -> list[ITransaction]

def run_excel_qif_merge(
    qif_in: Path, xlsx: Path, *, encoding: str = "utf-8"
) -> tuple[list[tuple[...]], list[ITransaction], list[ExcelTransaction]]
```

---

## File Conflict Risk Matrix

| Files | Agent A | Agent B | Agent C | Agent D | Risk |
|-------|---------|---------|---------|---------|------|
| `match_excel.py` | ✏️ (logging) | 📖 | ✏️ (refactor) | - | **Medium** |
| `match_session.py` | ✏️ (logging) | 📖 | ✏️ (refactor) | - | **Medium** |
| `convert_tab.py` | ✏️ (logging) | ✏️ (session) | - | ✏️ (shims) | **High** |
| `merge_tab.py` | ✏️ (logging) | ✏️ (session) | - | ✏️ (shims) | **High** |

**Legend:** ✏️ = Modifies, 📖 = Reads/uses

**Mitigation:** Agent A merges first, then B, then C, finally D

---

## Communication Protocol

### When starting work:
1. Update status in this file to 🔵 In Progress
2. Create branch as specified in agent work file
3. Follow complete checklist in agent-specific work file

### When blocked:
1. Update status to ⏸️ Blocked
2. Document blocker in "Blocked By" column
3. Coordinate with blocking agent

### When complete:
1. Update status to ✅ Complete
2. Post commit SHA
3. Notify dependent agents

---

## Core Policy Documents

All agents must read before starting:
- **[code-change.instructions.md](../.github/code-change.instructions.md)** - Required for every change
- **[unit-test-policy.md](unit-test-policy.md)** - Testing standards
- **[developer-tooling.md](developer-tooling.md)** - Required workflow
- **[code-remediation-phase-5-12.md](code-remediation-phase-5-12.md)** - Full roadmap