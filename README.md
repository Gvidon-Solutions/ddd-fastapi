# agentops-backend-kit

`agentops-backend-kit` is an agentic backend template for business automations
powered by long-running AI agents and Codex-style code execution.

It is built for the moment when "let's just ask Codex to automate this" stops
being a toy script and becomes a real backend concern: auth, jobs, queues,
state, errors, files, observability, tests, and maintainable architecture.

## Why It Exists

AI-assisted automation looks deceptively simple at the start. A business team
asks for an automation, you open Codex, Claude, OpenCode, or another agent
runner, ask for a small FastAPI service, wire a couple of endpoints, and it
feels like the feature is almost done.

Then the real system requirements arrive:

- not everyone should be able to trigger AI endpoints, so the system needs
  authentication and authorization;
- agent runs take minutes, so they must be durable background jobs;
- jobs need queueing, cancellation, retries, terminal states, visible errors,
  logs, files, and typed outputs;
- operators need to understand what happened without reading worker logs by
  hand;
- business logic needs tests that do not require booting the whole stack;
- future changes need to be safe enough for AI-assisted development.

Of course, you can keep prompting Codex, Claude, or another coding agent step by
step: "add this", "add that", "I forgot this too", "be careful", "write tests".
That works for a while, but it burns time and the straightforward approach
quickly turns the codebase into a tightly coupled mixture of routes, database
calls, queue calls, agent calls, status transitions, and serialization details.
The agent can also confidently report that everything is done while the actual
implementation hides brittle shortcuts, ad hoc
serialization, unclear ownership rules, and non-robust error handling inside a
large unstructured patch.
At that point the only reliable test is manual integration testing, and the
codebase stops making it obvious what is actually happening.

This repository is the result of working through several automation projects of
that shape. It uses the practical DDD/onion approach from
[`dddpy`](https://github.com/iktakahiro/dddpy), adapts it for agent jobs, and
adds local agent skills so humans and coding agents share the same definition of
done.

## What Is Inside

This project is a backend foundation for products where "run an agent" is a
real business operation, not a fire-and-forget helper function.

It gives you:

- FastAPI APIs for launching, listing, inspecting, and cancelling jobs;
- durable job state: `pending`, `queued`, `running`, terminal statuses, errors,
  events, files, and typed outputs;
- ARQ workers backed by Redis for long-running Codex auth/run workflows;
- SQLModel persistence adapters that convert database DTOs into domain objects;
- domain entities, value objects, repository ports, exceptions, and typed job
  contracts;
- use cases that keep application workflows separate from HTTP, SQL, Redis, and
  ARQ details;
- a disposable e2e smoke test that starts PostgreSQL, Redis, FastAPI, and the
  ARQ worker, then verifies the job API flow;
- `.agents/skills/` conventions that tell coding agents how to work in this
  repository.

### Architecture

The code is split by onion/DDD layers:

```text
backend/
  app/
    domain/          Pure entities, value objects, repository ports, exceptions
    usecase/         Application workflows and external capability ports
    infrastructure/  SQLModel, Redis, ARQ, file storage, security, DI adapters
    presentation/    FastAPI routes, dependencies, and API schemas
.agents/skills/      Local agent skills, DDD rules, and review conventions
```

The point is control. Each layer has a narrow job, and that makes the system
easier to understand, test, and extend:

- **Domain objects describe the business model directly.** Jobs, files, events,
  identifiers, inputs, outputs, and errors are explicit domain types, not loose
  dictionaries passed between handlers.
- **Use cases show application workflows without framework noise.** Creating,
  listing, cancelling, and executing jobs can be reviewed as business flows
  without mentally untangling HTTP, SQL, Redis, or ARQ details.
- **Repository and runtime ports give tests obvious fake/mock points.** Most
  behavior can be tested by replacing persistence, queues, file storage, Codex,
  or Redis with fakes instead of booting the whole application.
- **Infrastructure adapters contain the messy edges.** SQLModel DTOs, payload
  serialization, Redis records, ARQ enqueue/abort calls, file storage, and Codex
  CLI integration stay at the boundary.
- **Presentation routes stay transport-only.** Routes construct domain inputs,
  call one use case, map expected exceptions to HTTP responses, and serialize
  outputs back to API schemas.

This structure makes AI-assisted development much safer. You can inspect a file
path and immediately understand what kind of code is allowed there. You can
review whether business logic is complete without mentally untangling framework
details. You can test most behavior by replacing ports with fakes/mocks instead
of booting the whole application. The payoff is practical: better testability,
clearer failure handling, safer changes, and less manual integration testing.

### Stack

- **FastAPI** for the backend HTTP API.
- **Pydantic v2** and **pydantic-settings** for validation and typed config.
- **SQLModel**, **SQLAlchemy**, **PostgreSQL**, and **Alembic** for persistence.
- **Redis** and **ARQ** for background job runtime.
- **Codex CLI integration** for auth and code-execution workflows.
- **JWT authentication** with password hashing via `pwdlib`.
- **Sentry SDK** for application error reporting.
- **Pytest**, **Ruff**, **ty**, and **uv** for testing, linting, typing, and
  dependency management.
- **SOPS-encrypted environment files** for local, staging, and production
  configuration.

### Agent Skills

One of the main deliverables of this repository is the skill set under
`.agents/skills/`.

- `ddd-architecture` defines layers, entities, value objects, repository ports,
  exceptions, DTO boundaries, and use case shape.
- `ddd-jobs` defines how executable business jobs are created, dispatched,
  executed, cancelled, observed, and serialized.
- `ddd-presentation` defines FastAPI route and schema conventions.
- `ddd-review` defines what a reviewer must check before accepting changes.
- `ddd-testing` defines test layout and Arrange/Act/Assert discipline.

You can copy the whole backend, copy only selected skills, or assemble your own
`.agents/skills/` set depending on how strict you want the AI-assisted workflow
to be. The skills are part of the system: they make the architecture legible to
coding agents and provide a deterministic review checklist for humans.

### Use It

Use this repository as a starting point for your own agent-backed business
automation backend:

```bash
git clone <this-repository-url> my-agent-automation
cd my-agent-automation
git remote set-url origin git@github.com:your-org/my-agent-automation.git
```

Then adapt:

- `envs/` for local, staging, and production settings;
- `backend/app/config.py` for application metadata and defaults;
- `backend/app/domain/` for your domain model;
- `backend/app/usecase/` for your workflows;
- `backend/app/presentation/api/` for your HTTP API;
- `.agents/skills/` and `AGENTS.md` for your agent conventions.

Before deployment, change all default secrets and passwords, especially
`SECRET_KEY`, `FIRST_SUPERUSER_PASSWORD`, `POSTGRES_PASSWORD`, and any
Codex/OpenAI credentials or runtime volumes used by your deployment.

Run local checks:

```bash
uv run --project backend ruff check backend/app backend/tests
uv run --project backend ty check backend/app
uv run --project backend pytest
uv run --project backend python backend/scripts/e2e_jobs.py
```

Run Redis and the ARQ worker manually:

```bash
docker run -d --name agentops-backend-kit-redis -p 6379:6379 redis:7-alpine
uv run --project backend arq app.infrastructure.arq.worker.WorkerSettings
```

Codex CLI device-code login is exposed for backend admins:

```text
POST /api/v1/agents/codex/login/device
GET  /api/v1/agents/codex/login/device/{session_id}
GET  /api/v1/agents/codex/login/status
```

### Lineage

This repository intentionally builds on existing work:

- [`iktakahiro/dddpy`](https://github.com/iktakahiro/dddpy) is the main
  practical reference for DDD/onion architecture.
- [`iktakahiro/python-fastapi-ddd-skill`](https://github.com/iktakahiro/python-fastapi-ddd-skill)
  is the source reference for the DDD agent skills adapted into
  `.agents/skills/`.
- [`fastapi/full-stack-fastapi-template`](https://github.com/fastapi/full-stack-fastapi-template)
  is the FastAPI backend baseline used for authentication, users, settings,
  SQLModel, migrations, tests, and production-minded project structure.

The `sources/` directory is ignored by git and is used only as local reference
material.
