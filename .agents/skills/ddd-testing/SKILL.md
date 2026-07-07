---
name: ddd-testing
description: Use when adding or moving backend tests, choosing test scope, reviewing test layout, or enforcing that tests mirror source structure in this DDD repository.
---

# DDD Testing Skill

Use for pytest work and test layout review.

This repository uses an explicit AAA system: Arrange, Act, Assert.

## Test Layout

Tests mirror `backend/app` paths exactly enough that the tested source file is
obvious from the test location.

Mapping rules:

```text
backend/app/{layer}/{rest}.py
  -> backend/tests/{layer}/test_{rest_leaf}.py

backend/app/{layer}/{area}/{kind}/{name}.py
  -> backend/tests/{layer}/{area}/{kind}/test_{name}.py
```

Examples:

- `backend/app/domain/item/entities/item.py`
  -> `backend/tests/domain/item/entities/test_item.py`
- `backend/app/usecase/job/codex/codex_auth_job_use_case.py`
  -> `backend/tests/usecase/job/codex/test_codex_auth_job_use_case.py`
- `backend/app/infrastructure/sqlmodel/job/job_repository.py`
  -> `backend/tests/infrastructure/sqlmodel/job/test_job_repository.py`
- `backend/app/presentation/api/codex/routes/codex.py`
  -> `backend/tests/presentation/api/codex/routes/test_codex.py`

Rules:

- New tests must follow mirrored placement.
- Do not put unrelated behavior into a broad catch-all test file.
- If a test covers integration across several files, place it at the lowest
  common directory and make the filename name the behavior.
- Existing drift is not a reason to add more drift.

## Test Scope By Layer

Domain tests:

- use real domain objects;
- do not mock pure value objects/entities;
- test invariants, state transitions, equality, and domain exceptions;
- do not touch infrastructure.

Usecase tests:

- use fake/in-memory repository ports or `Mock(spec=...)`;
- verify repository calls when call shape matters;
- verify domain exceptions;
- verify orchestration and transaction-relevant decisions;
- do not use FastAPI clients.

Infrastructure tests:

- verify adapter behavior, DTO mapping, persistence, serialization, Redis/ARQ
  adapters, and filesystem behavior;
- may use real test databases/fakes as appropriate;
- assert conversion between DTOs and domain entities.

Presentation tests:

- verify HTTP status codes, response schemas, dependency overrides, auth/current
  user wiring, and exception mapping;
- do not duplicate usecase business tests.

## AAA Convention

Every test body must be readable as Arrange / Act / Assert.

Default shape:

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

Rules:

- Use `# Arrange`, `# Act`, and `# Assert` comments for phases present in the
  test body.
- Omit `# Arrange` only when all arrangement is provided by fixtures and there
  is no arrangement code in the test body.
- Use `# Act & Assert` when the action and assertion are one inseparable block,
  such as `with pytest.raises(...)`.
- Do not hide Act inside Arrange.
- Keep one behavior per test.

## DDD Testing Patterns

Value object tests cover valid and invalid construction:

```python
def test_title_accepts_valid_value() -> None:
    # Act
    title = Title("Hello")

    # Assert
    assert title.value == "Hello"


def test_title_rejects_empty_value() -> None:
    # Act & Assert
    with pytest.raises(TitleEmptyError):
        Title("")
```

Entity tests cover lifecycle:

```python
def test_job_file_keeps_job_identity(file: File) -> None:
    # Arrange
    attached_at = datetime.now(UTC)

    # Act
    job_file = JobFile.from_file(
        file,
        job_id=JOB_ID,
        role=JobFileRole.PRIMARY_OUTPUT,
        attached_at=attached_at,
    )

    # Assert
    assert job_file.job_id == JOB_ID
```

Usecase tests use fake ports or mocks:

```python
def test_create_job_persists_pending_job(jobs: InMemoryJobRepository) -> None:
    # Arrange
    use_case = new_create_job_use_case(jobs=jobs)
    job = ExampleJobV1.new(initiator=INITIATOR, input=ExampleInputV1())

    # Act
    use_case.execute(job)

    # Assert
    assert jobs.saved == [job]
```

Read `references/TESTING.md` for expanded patterns from the source DDD testing
skill adapted to this repository.

## Verification

Run:

```bash
uv run pytest backend/tests
uv run python tools/ddd_linter.py --check tests
```
