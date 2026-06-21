# skills-dddpy

FastAPI backend refactored toward a DDD/onion architecture style using the local
`sources/dddpy` project as the architectural reference and the FastAPI full-stack
template as the behavioral reference.

## Repository Layout

```text
backend/
  app/
    domain/          Pure entities, value objects, repository interfaces, exceptions
    usecase/         Application workflows and ports
    infrastructure/  SQLModel, email, security, and DI adapters
    presentation/    FastAPI routes, dependencies, and API schemas
sources/             Local references, intentionally not committed
.agents/skills/      Placeholder for local agent skills
```

## Development

```bash
uv run --project backend ruff check backend/app backend/tests
uv run --project backend mypy backend/app
uv run --project backend pytest
```

The `sources/` directory is ignored by git and is used only as reference material.
