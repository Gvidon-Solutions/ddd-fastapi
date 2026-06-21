# Backend

This backend keeps the public API shape of the FastAPI full-stack template while
moving implementation details into DDD-oriented layers.

## Layers

- `app/domain`: framework-free domain model.
- `app/usecase`: application workflows with repository and service ports.
- `app/infrastructure`: SQLModel repositories, DTOs, email helpers, security, DI.
- `app/presentation`: FastAPI routes, shared dependencies, and API schemas.

## Checks

```bash
uv run --project backend ruff check backend/app backend/tests
uv run --project backend ruff format --check backend/app backend/tests
uv run --project backend mypy backend/app
uv run --project backend pytest
```

## Tests

Tests are organized by layer:

- `tests/domain`
- `tests/usecase`
- `tests/infrastructure`
- `tests/integration`

Infrastructure tests use an in-memory SQLite database and do not require the
configured PostgreSQL service.
