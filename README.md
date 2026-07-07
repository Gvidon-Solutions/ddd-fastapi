# agentops-backend-kit

`agentops-backend-kit` is an agentic backend template for business automations
powered by long-running AI agents and Codex-style code execution.

The core idea is simple: a business team asks for automation, and the
implementation should not collapse into a one-off script once authorization,
background execution, job status, error handling, observability, persistence,
and tests appear.

This repository shows how to keep that workflow under control with FastAPI,
ARQ, SQLModel, Codex jobs, and a DDD/onion architecture adapted from
[`dddpy`](https://github.com/iktakahiro/dddpy).

The backend is async-first: FastAPI routes, use cases, repositories, ARQ
workers, and SQLModel database access all use `async`/`await`.

## What This Repo Is

This project is a backend foundation for products where "run an agent" is a
real business operation, not a fire-and-forget helper function.

It includes:

- HTTP APIs for launching and observing jobs.
- Durable job state: `pending`, `queued`, `running`, terminal statuses, errors,
  events, files, and typed outputs.
- ARQ workers for long-running Codex/auth/run workflows.
- Redis-backed transient state where it belongs, for example Codex auth polling.
- SQLModel persistence adapters that convert database DTOs into domain objects.
- Domain-level entities, value objects, repository ports, and exceptions.
- Explicit use cases for application actions.
- E2E smoke testing for the job flow.
- Local agent skills and a DDD linter that document and enforce the conventions.

## Technology Stack and Features

- **FastAPI** for the backend HTTP API.
- **Pydantic v2** and **pydantic-settings** for validation and typed
  configuration.
- **SQLModel** and **SQLAlchemy** for persistence mapping.
- **PostgreSQL** as the production database target.
- **Alembic** for database migrations.
- **Redis** as the runtime backend for queues and transient job state.
- **ARQ** for long-running background jobs.
- **Codex CLI integration** for auth and code-execution job workflows.
- **JWT authentication** with password hashing via `pwdlib`.
- **Email utilities** inherited from the FastAPI full-stack template baseline.
- **Sentry SDK** integration for application error reporting.
- **Pytest** for tests.
- **Ruff** for linting and import formatting.
- **ty** for static type checking.
- **uv** workspaces for dependency management.
- **SOPS-encrypted environment files** for local, staging, and production
  configuration.
- **DDD linter** for repository-specific architecture conventions.
- **Disposable e2e job smoke test** that starts PostgreSQL, Redis, FastAPI, and
  the ARQ worker, then verifies the job API flow.

## Agent Skills as a Deliverable

One of the main outputs of this repository is the skill set under
`.agents/skills/`.

These skills describe how an AI coding agent should work inside a DDD/onion
backend:

- `ddd-architecture` explains the layer model, entity/value object rules,
  repository ports, exceptions, DTO boundaries, and use case shape.
- `ddd-jobs` explains how executable business jobs are created, dispatched,
  executed, cancelled, observed, and serialized.
- `ddd-presentation` explains FastAPI route and schema conventions.
- `ddd-review` defines what a reviewer must check before accepting changes.
- `ddd-testing` explains the test layout and Arrange/Act/Assert discipline.

They are intentionally separate from the application code. Users can copy the
whole backend, copy only selected skills, or assemble their own `.agents/skills/`
set depending on how strict they want the AI-assisted workflow to be.

The skills are not a decorative documentation folder. They are part of the
system: they tell coding agents what "done" means in this repository and give
reviewers a deterministic checklist for architecture, jobs, presentation, and
tests.

## Why It Exists

AI-assisted automation looks easy at the start. Open Codex, Claude, OpenCode, or
another agent runner, ask for a small FastAPI service, wire a couple of
endpoints, and it feels like the feature is almost done.

Then the real system requirements arrive:

- users need authentication and authorization;
- agent runs take minutes, so they must be jobs;
- jobs need queueing, cancellation, retries, terminal states, and visible errors;
- outputs and logs need to be stored and connected back to the run;
- operators need to understand what happened without reading worker logs by hand;
- business logic needs tests that do not require running the whole stack;
- future changes need to be safe enough for AI-assisted development.

The usual reaction is to add more instructions to Codex, Claude, or another
coding agent: "be careful", "follow the architecture", "do not break anything",
"write tests". That helps only until the next ambiguous change. If the codebase
itself does not expose clear boundaries, the agent has to infer them from prose,
and the team is back to manually checking whether the generated code accidentally
crossed a hidden line.

Without a strict architecture, the code quickly turns into a tightly coupled
mixture of routes, database calls, queue calls, agent calls, status transitions,
and serialization details. At that point the only reliable test is manual
integration testing, and the codebase stops making it obvious what is actually
happening.

This repository is the result of working through several automation projects of
that shape. The architecture is based on the practical DDD/onion approach from
[`dddpy`](https://github.com/iktakahiro/dddpy), then adjusted for agent jobs,
Codex auth, Codex execution, background workers, and observable job history.

## References and Lineage

This repository intentionally builds on existing work instead of pretending the
architecture appeared from nowhere:

- [`iktakahiro/dddpy`](https://github.com/iktakahiro/dddpy) is the main
  practical reference for the DDD/onion architecture style used here.
- [`iktakahiro/python-fastapi-ddd-skill`](https://github.com/iktakahiro/python-fastapi-ddd-skill)
  is the source reference for the DDD agent skills adapted into
  `.agents/skills/`.
- [`fastapi/full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template)
  is the FastAPI backend baseline used as the behavioral and infrastructure
  reference for authentication, users, settings, SQLModel, migrations, tests,
  and production-minded project structure.

## Why DDD + Onion Architecture Here

The point is not academic purity. The point is control.

When the system is split into domain, use cases, infrastructure, and
presentation, the codebase gives you natural boundaries:

- Domain objects describe the business model directly.
- Use cases show application workflows without HTTP, SQL, Redis, or ARQ noise.
- Repository and runtime ports give tests obvious mock points.
- Infrastructure adapters contain database, queue, Redis, file storage, and
  serialization details.
- Presentation routes only translate HTTP into use case calls and HTTP
  responses.

That structure makes AI-assisted development much safer. You can inspect a file
path and immediately understand what kind of code is allowed there. You can
review whether business logic is complete without mentally untangling framework
details. You can test most behavior by replacing ports with fakes instead of
booting the whole application.

## What This Buys You

- **Testability:** domain and use case tests can mock ports naturally because
  dependencies are explicit interfaces.
- **Observability:** jobs produce status, errors, files, and events that can be
  read through API endpoints.
- **Durability:** long-running work is represented as persisted jobs, not hidden
  in request handlers.
- **Change safety:** conventions make it obvious where new behavior belongs.
- **AI-readability:** agents can navigate the project by layer and file name
  instead of guessing where logic is hidden.
- **Operational clarity:** worker execution, cancellation, auth polling, and
  result serialization are explicit parts of the system.

## Repository Layout

```text
backend/
  app/
    domain/          Pure entities, value objects, repository interfaces, exceptions
    usecase/         Application workflows and ports
    infrastructure/  SQLModel, email, security, and DI adapters
    presentation/    FastAPI routes, dependencies, and API schemas
.agents/skills/      Local agent skills, DDD rules, and review conventions
```

The same layering rules are documented for agents in `.agents/skills/` and
summarized in `AGENTS.md`.

## How To Use It

You can use this repository as a starting point for your own agent-backed
business automation backend.

The simplest path is to copy or clone the project:

```bash
git clone <this-repository-url> my-agent-automation
cd my-agent-automation
```

Then set a new Git remote:

```bash
git remote set-url origin git@github.com:your-org/my-agent-automation.git
```

Update project-specific settings:

- environment files under `envs/`;
- application metadata in `backend/app/config.py`;
- domain areas under `backend/app/domain/`;
- use cases under `backend/app/usecase/`;
- API routes and schemas under `backend/app/presentation/api/`;
- agent conventions under `.agents/skills/`, if your team wants different
  rules.

Before using it for a real deployment, change all default secrets and passwords,
especially:

- `SECRET_KEY`;
- `FIRST_SUPERUSER_PASSWORD`;
- `POSTGRES_PASSWORD`;
- any Codex/OpenAI credentials or runtime volumes used by your deployment.

If you only want the conventions, copy `.agents/skills/` and `AGENTS.md` into an
existing repository and adapt the references to your project structure.

## Development

```bash
uv run --project backend ruff check backend/app backend/tests
uv run --project backend ty check backend/app
uv run --project backend pytest
uv run --project backend python backend/scripts/e2e_jobs.py
```

## Redis and ARQ

Redis is used as the ARQ job backend for Codex jobs.

```bash
docker run -d --name agentops-backend-kit-redis -p 6379:6379 redis:7-alpine
uv run --project backend arq app.infrastructure.arq.worker.WorkerSettings
```

The reproducible job e2e smoke test starts disposable PostgreSQL and Redis
containers, launches the FastAPI app and ARQ worker, creates a Codex auth job via
HTTP, and verifies that it moves from `pending` to `succeeded` with events,
result, list, and detail endpoints:

```bash
uv run --project backend python backend/scripts/e2e_jobs.py
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
