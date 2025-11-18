# Unit Test Policy

Unit test policy. Every new or modified unit test must adhere to the following guidelines.

- **Independence**: Ensure tests can run in any order without impacting each other. Use mocks or stubs to isolate dependencies.
- **Isolation**: Target a single function or method per test so failures pinpoint the faulty unit.
- **Fast Execution**: Keep tests quick to maintain rapid feedback loops.
- **Determinism**: Avoid flaky behavior; given the same inputs, tests must produce the same outputs.
- **Readability and Maintainability**: Write clear test names, structure, and assertions.
- **Comprehensive Coverage**: Exercise critical paths and edge conditions without chasing 100% coverage for its own sake.
- **Scenario Completeness**:
  - Positive flows with valid inputs.
  - Negative flows for invalid or missing inputs.
  - Edge cases and boundary conditions.
  - Error handling expectations.
  - Concurrency behavior when relevant.
  - State transitions for stateful components.
- **Clear Failure Messages**: Assertions should make failures easy to diagnose.
- **Arrange-Act-Assert Pattern**: Organize code into setup, execution, and verification blocks.
- **Avoid External Dependencies**: Remove reliance on external services; mock or stub them when necessary.
- **Document Intent**: Every test must include a docstring summarizing its purpose.
- **Policy Audit**: After writing tests, confirm they comply with this policy before submission.
