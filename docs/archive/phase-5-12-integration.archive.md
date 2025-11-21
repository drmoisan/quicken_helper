# Phase 5-12 Integration Sequence

## Wave 1: Parallel Foundation (Agents A + C)
- Agent A: Logging + DataSession API
- Agent C: Match pipeline modernization
- **No conflicts** - different file sets

## Wave 2: Tab Refactoring (Agent B)
- **Requires:** Agent A complete (DataSession API stable)
- **Parallel with:** Agent C (if Agent C careful about API stability)
- **Integration point:** tabs will eventually consume Agent C's match API

## Wave 3: Cleanup (Agent D)
- **Requires:** All prior agents complete
- Sequential cleanup and polish work

## Merge Order
1. Agent A → refactor/typed-data-model (establishes DataSession + logging)
2. Agent C → refactor/typed-data-model (match pipeline ready for tabs)
3. Agent B → refactor/typed-data-model (tabs use DataSession + new match API)
4. Agent D → refactor/typed-data-model (cleanup shims, centralize I/O, error handling)