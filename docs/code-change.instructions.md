---
applyTo: "**"
---
# Agent Code Change Policy:

Please adhere to the following policy every time you make **any change** to code. This includes but is not limited to adding, removing, or changing any code, modules, packages, tests or their components.

## Before making changes

* [ ] Clarify the objective. Begin reasoning from clearly stated assumptions or axioms.
* [ ] Review [unit-test-policy.md](../docs/unit-test-policy.md), [developer-tooling](../docs/developer-tooling.md), and [README.md](../docs/README.md)
* [ ] Read existing change documentation (e.g., [code-remediation-phase-0-4](../docs/code-remediation-phase-0-4.md), and [code-remediation-phase-5.12](../docs/code-remediation-phase-5-12.md))
* [ ] Document the plan to make changes. If it is part of an existing change plan, make any relevant updates to the plan before executing.

## Python Coding Standards

These rules are **requirements**, not suggestions. Code that doesn’t follow them should be treated as incorrect.

### 1. Tooling & Baseline

1. **Formatting**

   * All code must be formatted with **Black** (default settings).
   * Do not hand-format; if a diff disagrees with Black, Black wins.
2. **Linting**

   * Code must pass **Ruff** with the project’s configuration.
   * Do not disable rules unless strictly necessary; if you must, use a **targeted, single-line** `# noqa` with a comment explaining why.
3. **Typing**

   * Code must be **fully type-annotated** and pass **Pyright**.
   * No `Any` unless absolutely unavoidable. If `Any` is used, document why in a comment.
4. **Testing**

   * All new logic must be covered by **Pytest** tests.
   * Follow the project’s [unit-test-policy.md](unit-test-policy.md)

---

### 2. Design Principles

High-level design priorities:

1. **Simplicity first**

   * Prefer the simplest design that works and is easy to read.
   * Avoid cleverness and deep indirection. The next maintainer should be able to understand a module in one reading.
2. **Reusability**

   * Factor out logic that is clearly reusable into small methods or pure functions.
   * Avoid copy-paste; share behavior via composition, helper methods, or shared base classes/interfaces.
3. **Extensibility**

   * Design public APIs so they can be extended without breaking callers:

     * Prefer keyword arguments with defaults.
     * Prefer composition over inheritance when possible.
     * Use protocols/ABCs to support multiple implementations behind an interface.
4. **Separation of concerns**

   * Keep **pure logic** (transforms, calculations, parsing) separate from:

     * I/O (disk, network, DB)
     * UI / CLI
     * Framework-specific glue.
   * Orchestration code (e.g., “main” pipeline classes) may depend on many things; pure core logic should depend on very little.

---

### 3. Classes, Functions, and APIs

**Overall rule:**
Use **strongly typed classes** to model domain concepts and workflows. Use **functions** for small, stateless helpers and glue code.

#### 3.1 Prefer classes for domain concepts and workflows

Create a class when at least one is true:

* There is a **clear domain concept** with data + behavior

  * e.g. `QifTransaction`, `LexileCorpus`, `ContactMatcher`, `CorpusPipeline`.
* You have **state + invariants** that should travel together

  * e.g. a `LexileModel` that must keep weights, vocabulary, and metadata in sync.
* You expect **multiple implementations** behind a common interface

  * e.g. `ITextSource` with `EpubTextSource`, `GutenbergTextSource`, etc.
* You are modeling a **multi-step workflow** that shares context

  * e.g. `CorpusPipeline.download()`, `.normalize()`, `.index()`, `.export()`.

When you use classes:

* Prefer **`@dataclass`** for value objects (frozen where possible).
* Keep methods **small and focused**; a method should do one conceptual thing.
* Avoid “God objects” that know about too many unrelated concerns.

#### 3.2 Use functions for small, pure helpers

Create a standalone function when:

* The operation is **pure, stateless, and simple**:

  * e.g. `normalize_whitespace(text: str) -> str`
  * e.g. `slugify(title: str) -> str`
* It’s a **small helper** that doesn’t naturally belong on a specific domain class.
* It is a **simple transformation** from inputs to outputs.

Rules for functions:

* Fully annotate parameters and return types.
* Name them by what they do (`parse_qif_file`, `compute_lexile_score`).
* Keep them short and readable; avoid long, branching functions.

#### 3.3 Interfaces and typing

* Use **`Protocol`** or **abstract base classes** when multiple implementations are likely (e.g. different storage backends or text sources).
* Public methods and functions must be fully type-annotated and **Pyright-clean**.
* Avoid static-method-only “utility” classes. Prefer modules + functions for that.

---

### 4. Error Handling, Logging, and Contracts

1. **Error handling**

   * Fail **fast and explicitly**: raise clear, specific exceptions when invariants are violated.
   * Don’t silently ignore errors or broad-catch (e.g. `except Exception:`) unless you immediately re-raise with context.
2. **Logging**

   * Use the project’s logging pattern (e.g. `logging` module) instead of `print`.
   * Log at appropriate levels (`debug`, `info`, `warning`, `error`) and include enough context to debug issues.
3. **Contracts / invariants**

   * Enforce invariants at construction time (`__post_init__` for dataclasses or `__init__`).
   * Use assertions only for **internal sanity checks**, not user-facing error handling.

---

### 5. Module & File Structure

1. Keep modules **cohesive**:

   * A module should have a clear purpose (e.g. “QIF parsing,” “Lexile model,” “corpus download”).
   * Avoid dumping unrelated classes/functions into the same file.
2. Public vs internal

   * Make the public surface area **small and intentional**.
   * Use `_internal` helpers and `_`-prefixed module members for things that should not be used outside the module.
3. Imports

   * Prefer absolute imports within the project.
   * Avoid circular dependencies; if they appear, refactor shared logic into a lower-level module.

---

### 6. Naming, Docs, and Comments

1. Naming

   * Use **PEP 8** naming:

     * `snake_case` for functions and variables.
     * `PascalCase` for classes.
   * Names should be descriptive, not abbreviated, unless the abbreviation is standard (`id`, `url`, `db`).
2. Docstrings

   * Public classes and methods should have a short docstring describing:

     * What it does.
     * Important arguments.
     * What it returns or side effects.
3. Comments

   * Comment **why**, not what. The code should generally explain *what*.
   * If you use workarounds or non-obvious patterns, add a short comment explaining the reasoning.

---

### 7. Performance, I/O, and Dependencies

1. Performance

   * Prefer clarity first; optimize only where there is a demonstrated need.
   * Avoid O(N²) or worse algorithms on large inputs unless justified.
2. I/O boundaries

   * Isolate I/O (disk, network, APIs) into specific classes or modules.
   * Core domain logic should be testable **without** touching the network or filesystem.
3. Dependencies

   * Use only the libraries already approved in the project unless specifically told to add more.
   * If adding a dependency is unavoidable, choose a well-maintained, widely used package, and document why it’s required.

---

### 8. How to Interact with Existing Code

1. Follow existing patterns:

   * Where the repo already has a clear style (e.g. how pipelines or models are structured), **match that style**.
   * If you need to improve an existing pattern, keep it **compatible** with current usages.
2. API changes

   * Avoid breaking public APIs. If a breaking change is necessary, call it out clearly in comments or the PR description.
3. Tests as specification

   * Treat existing unit tests as **part of the spec**.
   * When adding new behavior, add tests that make the behavior explicit.

## After Making Changes

1. Re-run formatting, linting, type checking, and testing
   * Please run these sequentially.
   * If any step produces an error, please fix it and re-start the sequence
   * Do no stop iterating until all steps are complete without error
2. Summarize key changes made and how it relates the objective.
   * Please include the rationale for the change
   * Explain any design choices and other options explored
3. Update any supporting documents (e.g., [README](../docs/README.md)) and any workplan that was created to show progress
4. Provide clear development next steps. If development is complete, please provide detailed instructions on usage.
