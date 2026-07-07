# Testing Patterns

This reference is adapted from
`sources/python-fastapi-ddd-skill/skills/python-fastapi-ddd-testing-skill`.

## Test Tree Mirrors Source Tree

The test path must make the tested source path obvious.

```text
backend/app/domain/{area}/entities/{entity}.py
  -> backend/tests/domain/{area}/entities/test_{entity}.py

backend/app/domain/{area}/value_objects/{value_object}.py
  -> backend/tests/domain/{area}/value_objects/test_{value_object}.py

backend/app/usecase/{area}/{action}_{area}_use_case.py
  -> backend/tests/usecase/{area}/test_{action}_{area}_use_case.py

backend/app/infrastructure/{adapter}/{area}/{thing}.py
  -> backend/tests/infrastructure/{adapter}/{area}/test_{thing}.py

backend/app/presentation/api/{area}/routes/{route_module}.py
  -> backend/tests/presentation/api/{area}/routes/test_{route_module}.py
```

If one test file covers multiple source files, place it at the lowest common
directory and name the behavior explicitly.

## AAA System

Use Arrange / Act / Assert comments in every test body where those phases exist.

```python
def test_find_by_id_returns_entity(repository: InMemoryRepository) -> None:
    # Arrange
    entity = Entity.new(name="A")
    repository.add(entity)
    use_case = FindEntityUseCaseImpl(repository)

    # Act
    result = use_case.execute(entity.id)

    # Assert
    assert result == entity
```

When arrangement is entirely in fixtures:

```python
def test_entity_has_expected_default(entity: Entity) -> None:
    # Act
    result = entity.status

    # Assert
    assert result == EntityStatus.ACTIVE
```

When action and assertion are inseparable:

```python
def test_find_by_id_raises_when_missing(use_case: FindEntityUseCase) -> None:
    # Act & Assert
    with pytest.raises(EntityNotFoundError):
        use_case.execute(MISSING_ID)
```

## Value Object Tests

Value objects are immutable and validated. Test accepted values, rejected
values, equality, and derived behavior.

```python
def test_todo_title_accepts_valid_value() -> None:
    # Act
    title = TodoTitle("Hello")

    # Assert
    assert title.value == "Hello"


def test_todo_title_rejects_empty_value() -> None:
    # Act & Assert
    with pytest.raises(TodoTitleEmptyError):
        TodoTitle("")
```

## Entity Tests

Entities have identity and lifecycle. Test state transitions and invariants.

```python
def test_todo_complete_sets_completed_status() -> None:
    # Arrange
    todo = Todo.create(TodoTitle("Test"))
    todo.start()

    # Act
    todo.complete()

    # Assert
    assert todo.status == TodoStatus.COMPLETED
```

For time-based logic, pass explicit timestamps into domain methods when
possible so tests stay deterministic.

## Usecase Tests

Usecase tests verify orchestration through domain ports.

Use `Mock(spec=RepositoryPort)` when strict call shape matters:

```python
def test_create_todo_calls_save() -> None:
    # Arrange
    repository = Mock(spec=TodoRepository)
    use_case = CreateTodoUseCaseImpl(repository)
    title = TodoTitle("Test")

    # Act
    todo = use_case.execute(title=title)

    # Assert
    repository.save.assert_called_once_with(todo)
```

Use fake repositories when behavior is easier to express with state:

```python
def test_cancel_job_marks_pending_job_cancelled() -> None:
    # Arrange
    jobs = InMemoryJobRepository()
    runtime = FakeJobRuntime()
    use_case = CancelJobUseCaseImpl(jobs=jobs, runtime=runtime)
    job = ExampleJobV1.new(initiator=INITIATOR, input=ExampleInputV1())
    jobs.add(job)

    # Act
    use_case.execute(job.id, current_user_id=INITIATOR.external_id)

    # Assert
    assert jobs.get(job.id).status == JobStatus.CANCELLED
```

## Infrastructure Tests

Infrastructure tests verify real adapter behavior:

- SQLModel DTO <-> domain conversion;
- repository persistence and atomic updates;
- payload codec round trips;
- ARQ worker binding behavior;
- Redis/file storage adapters with fakes or isolated test resources.

## Presentation Tests

Presentation tests verify transport behavior:

- response status and schema;
- dependency overrides;
- current-user/auth wiring;
- expected exception-to-HTTP mapping.

Do not retest usecase business rules in route tests. Route tests should prove
that the route calls the right usecase contract and maps outputs/errors.
