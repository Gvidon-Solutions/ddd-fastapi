---
name: skills-ddd-testing
description: Use when adding or moving backend tests, choosing test scope, reviewing test layout, or enforcing that tests mirror source structure in this DDD repository.
---

# DDD Testing Skill

Use for pytest work and test layout review.

## Test Layout

Tests mirror source paths:

- `backend/app/domain/item/entities/item.py`
  -> `backend/tests/domain/item/entities/test_item.py`
- `backend/app/usecase/job/codex/codex_auth_job_use_case.py`
  -> `backend/tests/usecase/job/codex/test_codex_auth_job_use_case.py`
- `backend/app/infrastructure/sqlmodel/job/job_repository.py`
  -> `backend/tests/infrastructure/sqlmodel/job/test_job_repository.py`
- `backend/app/presentation/api/codex/routes/codex.py`
  -> `backend/tests/presentation/api/codex/routes/test_codex.py`

Existing tests may lag this convention; new tests should not add more drift.

## Test Scope

- Domain tests use real domain objects and no infrastructure.
- Usecase tests use fake or in-memory repository ports.
- Infrastructure tests verify adapter behavior and conversion.
- Presentation tests verify HTTP mapping and DI override behavior.

## AAA Convention

Every test should read as Arrange / Act / Assert:

```python
def test_behavior() -> None:
    # Arrange
    repository = InMemoryRepository()
    use_case = new_use_case(repository)

    # Act
    result = use_case.execute(...)

    # Assert
    assert result == expected
```

Always include phase comments for phases that exist in the test body. Use
`# Arrange`, `# Act`, and `# Assert` by default. Omit `# Arrange` when setup is
fully provided by fixtures and there is no arrangement code in the test body.
Use `# Act & Assert` when the action and assertion are one inseparable block,
such as `with pytest.raises(...)`.

## Review

Run:

```bash
uv run pytest backend/tests
uv run python tools/ddd_linter.py --check tests
```
