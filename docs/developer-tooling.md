# Developer Tooling

This document summarizes the core developer tooling for `quicken_helper`: what it is for, and the basic commands you should run during everyday development.

All commands below assume you are in the project root and have run:

- `poetry install` – create the managed `.venv` with runtime + dev dependencies.
- `poetry run pre-commit install` – install local git hooks that mirror CI behavior.

You can either activate the Poetry virtualenv (`poetry shell`) or prefix commands with `poetry run`.

## Formatting – Black

- **Purpose**: Enforce a consistent, automatic code style across the project.
- **Primary command**:  
  - Format in place: `poetry run black .`  
  - Check only (no writes): `poetry run black --check .`
- **When to use**: Before committing, or whenever you touch Python code.

## Linting – Ruff

- **Purpose**: Catch common bugs and style issues (imports, unused variables, etc.).
- **Primary command**: `poetry run ruff check`
  - Configuration lives in `pyproject.toml` under `[tool.ruff]` and `[tool.ruff.lint]`.
- **When to use**: After formatting and before committing or opening a PR.

## Type Checking – Pyright

- **Purpose**: Enforce strict typing (`typeCheckingMode = "strict"`) for the `quicken_helper` package.
- **Primary command**: `poetry run pyright`
  - Configuration: `[tool.pyright]` in `pyproject.toml` (tests are currently excluded).
- **When to use**: Before any non-trivial change is merged. Avoid adding new Pyright errors.

## Testing – Pytest

- **Purpose**: Run the automated test suite to validate behavior.
- **Primary command**: `poetry run pytest`
  - Test configuration: `pytest.ini` and `docs/unit-test-policy.md`.
- **When to use**: Before pushing changes, and after any change to production code or tests.

## Coverage – Coverage.py

- **Purpose**: Measure and report how much of the codebase is exercised by tests.
- **Typical commands**:
  - Run tests with coverage: `poetry run coverage run -m pytest`
  - Generate HTML report: `poetry run coverage html` (open `htmlcov/index.html`).
- **When to use**: When validating how well new or refactored code is covered by tests.

## Pre-commit Hooks

- **Purpose**: Automatically run checks on changed files before every commit.
- **Configuration**: `.pre-commit-config.yaml` (Black, Ruff, Pyright, plus custom grep hooks).
- **Setup (once per machine)**: `poetry run pre-commit install`
- **Manual run** (optional): `poetry run pre-commit run --all-files`
- **Behavior**:
  - Reject commits that contain `DELETE_ME` or `REMOVE_BEFORE_MERGE` markers in Python code.
  - Format, lint, and type-check Python files according to project configuration.

## VS Code Tasks

If you use VS Code, `.vscode/tasks.json` defines one-click tasks that wrap the commands above:

- `Black: format` – runs `poetry run black .`
- `Ruff: lint` – runs `poetry run ruff check`
- `Pyright: type-check` – runs `poetry run pyright`
- `Pyright: log output` – runs Pyright and writes a detailed log to `pyright.log`
- `Pytest: run tests` – runs `poetry run pytest`
- `Coverage: html report` – runs tests with coverage and generates an HTML report
- `Coverage: Codecov upload` – prepares coverage XML and calls `codecov` (requires `CODECOV_TOKEN`)

You can invoke these via **Terminal → Run Task…** (or the Command Palette: “Tasks: Run Task”).

## Profiling – VizTracer

- **Purpose**: Profile and visualize performance hotspots in the codebase.
- **Usage examples**:
  - Profile a specific test module:  
    `poetry run viztracer -m pytest tests/path/to/test_module.py`
  - Profile a script or entry point:  
    `poetry run viztracer python -m quicken_helper.gui_viewers.app`
- **Output**: VizTracer produces a trace file that you can open in a browser to inspect timelines and call stacks.

## Recommended Local Workflow

For each change, aim to follow this sequence:

1. Format: `poetry run black .`
2. Lint: `poetry run ruff check`
3. Type-check: `poetry run pyright`
4. Test: `poetry run pytest`
5. (Optional) Coverage / profiling for larger refactors

This keeps the codebase consistent, typed, and well-tested as it evolves.

