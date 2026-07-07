# skills-dddpy

FastAPI backend refactored toward a DDD/onion architecture style using the local
`sources/dddpy` project as the architectural reference and the FastAPI full-stack
template as the behavioral reference.

The backend is async-first: FastAPI routes, use cases, repositories, and SQLModel
database access all use `async`/`await`.

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
uv run --project backend ty check backend/app
uv run --project backend pytest
uv run --project backend python tools/e2e_jobs.py
```

## Redis and ARQ

Redis is used as the ARQ job backend for Codex jobs.

```bash
docker run -d --name skills-dddpy-redis -p 6379:6379 redis:7-alpine
uv run --project backend arq app.infrastructure.arq.worker.WorkerSettings
```

The reproducible job e2e smoke test starts disposable PostgreSQL and Redis
containers, launches the FastAPI app and ARQ worker, creates a Codex auth job via
HTTP, and verifies that it moves from `pending` to `succeeded` with events,
result, list, and detail endpoints:

```bash
uv run --project backend python tools/e2e_jobs.py
```

Codex CLI device-code login is exposed for backend admins:

```text
POST /api/v1/agents/codex/login/device
GET  /api/v1/agents/codex/login/device/{session_id}
GET  /api/v1/agents/codex/login/status
```

## Environments

Environment files `envs/local.env`, `envs/staging.env`, and
`envs/production.env` are encrypted with SOPS using the repository `.sops.yaml`
rules. `envs/example.env` is a plaintext template.

```bash
sops envs/local.env
sops --decrypt envs/local.env
sops exec-env envs/local.env 'uv run --project backend fastapi dev app/main.py'
```

The `sources/` directory is ignored by git and is used only as reference material.
