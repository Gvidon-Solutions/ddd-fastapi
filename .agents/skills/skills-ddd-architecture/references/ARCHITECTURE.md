# Onion Architecture for Python DDD

## Layer Diagram

```
┌─────────────────────────────────────────┐
│         Presentation Layer              │  FastAPI handlers, Pydantic schemas
├─────────────────────────────────────────┤
│           UseCase Layer                 │  Application business rules
├─────────────────────────────────────────┤
│        Infrastructure Layer             │  DB repos, DTOs, DI config
├─────────────────────────────────────────┤
│           Domain Layer                  │  Entities, Value Objects, Repo interfaces
└─────────────────────────────────────────┘
```

**Dependencies flow inward only.** Outer layers depend on inner layers; inner layers know nothing about outer layers.

## Layer Responsibilities

### Domain Layer (Innermost)

The core of the application. Contains pure business logic with **zero external dependencies**.

**Contains:**
- **Entities**: Objects with identity and lifecycle (e.g., `Todo`)
- **Value Objects**: Immutable typed values (e.g., `TodoId`, `TodoTitle`, `TodoStatus`)
- **Repository Interfaces**: Abstract persistence contracts (`TodoRepository(ABC)`)
- **Domain Exceptions**: Business rule violation errors (`TodoNotFoundError`)

**Rules:**
- No imports from FastAPI, SQLAlchemy, Pydantic, or any framework
- No I/O operations (no database, no HTTP, no filesystem)
- All validation logic for business rules

### Infrastructure Layer

Implements domain interfaces and integrates with external systems.

**Contains:**
- **Repository Implementations**: `TodoRepositoryImpl` using SQLAlchemy
- **DTOs**: `TodoDTO` mapping entities to/from database models
- **Database Configuration**: Engine, session, table creation
- **Dependency Injection**: FastAPI `Depends()` wiring

**Rules:**
- Implements domain interfaces (e.g., `TodoRepository`)
- Converts between domain entities and persistence models via DTOs
- Manages session lifecycle (commit/rollback/close)

### UseCase Layer

Orchestrates domain objects to accomplish application actions.

**Contains:**
- **Use Case Interfaces**: Abstract definitions (`CreateTodoUseCase(ABC)`)
- **Use Case Implementations**: Concrete business workflows
- **Factory Functions**: `new_create_todo_usecase()`

**Rules:**
- One use case class per application action
- Single public `execute()` method
- Receives and returns domain objects (not DTOs or schemas)
- Raises domain exceptions for business rule violations

### Presentation Layer (Outermost)

Handles HTTP requests and responses.

**Contains:**
- **Route Handlers**: FastAPI endpoint functions
- **Request Schemas**: Pydantic models for input validation (`TodoCreateSchema`)
- **Response Schemas**: Pydantic models for serialization (`TodoSchema`)
- **Error Messages**: HTTP error response models

**Rules:**
- Converts HTTP input to domain Value Objects
- Calls use case `execute()` methods
- Converts domain entities to response schemas
- Maps domain exceptions to HTTP status codes

## Data Flow

### Request Flow (Create Todo)

```
POST /todos { "title": "Buy milk" }
    │
    ▼
Presentation: TodoCreateSchema validates JSON
    │
    ▼
Presentation: Constructs TodoTitle("Buy milk")
    │
    ▼
UseCase: CreateTodoUseCaseImpl.execute(title)
    │
    ▼
Domain: Todo.create(title) → new Todo entity
    │
    ▼
Infrastructure: TodoRepository.save(todo)
    │
    ▼
Infrastructure: TodoDTO.from_entity(todo) → INSERT
    │
    ▼
Presentation: TodoSchema.from_entity(todo) → JSON response
```

### Dependency Injection Chain

```
FastAPI Request
    ↓
get_session() → SQLAlchemy Session (commit/rollback managed here)
    ↓
get_todo_repository(session) → TodoRepositoryImpl
    ↓
get_create_todo_usecase(repository) → CreateTodoUseCaseImpl
    ↓
Route handler receives usecase, calls execute()
```

## Application Bootstrap

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()    # Setup
    yield
    engine.dispose()   # Teardown

app = FastAPI(title="DDD Todo API", lifespan=lifespan)

todo_handler = TodoApiRouteHandler()
todo_handler.register_routes(app)
```

## Adding a New Aggregate

When adding a new domain concept (e.g., `User`):

1. **Domain**: Create `domain/user/entities/`, `value_objects/`, `repositories/`, `exceptions/`
2. **Infrastructure**: Create `infrastructure/sqlite/user/user_dto.py` and `user_repository.py`
3. **UseCase**: Create `usecase/user/create_user_usecase.py`, etc.
4. **Presentation**: Create `presentation/api/user/handlers/`, `schemas/`, `error_messages/`
5. **DI**: Add `get_user_repository()` and `get_*_user_usecase()` functions to `injection.py`
6. **Bootstrap**: Register new route handler in `main.py`

Each aggregate is self-contained within its subdirectory across all layers.

## Aggregates and Subaggregates

Aggregates and subaggregates are allowed.

Backend domain code must keep aggregate structure explicit:

```text
backend/app/domain/{area}/
  entities/
  value_objects/
  repositories/
  exceptions/

backend/app/domain/{area}/{aggregate}/
  entities/
  value_objects/
  repositories/
  exceptions/

backend/app/domain/{area}/{aggregate}/{subaggregate}/
  entities/
  value_objects/
  repositories/
  exceptions/
```

Aggregate rules:

- Put an aggregate under the domain area that owns its business language.
- Put a subaggregate under the aggregate that owns its lifecycle and invariants.
- Keep entities in `entities/`, value objects in `value_objects/`, repository
  ports in `repositories/`, and domain exceptions in `exceptions/`.
- Do not flatten aggregate-owned entities into a shared folder when the
  aggregate boundary is meaningful.
- Do not create cross-area aggregate folders just to reuse code. Shared concepts
  need an explicit shared domain owner.

## Jobs

Jobs are durable, typed domain entities. A job is not a raw queue message and
not a transport DTO.

Job code is split across the same Onion layers:

```text
backend/app/domain/job/base/
  entities/job.py
  entities/job_contract.py
  entities/job_event.py
  entities/job_file.py
  repositories/job_repository.py
  value_objects/
  exceptions/

backend/app/domain/job/{business_job}_job_use_case/
  entities/{business_job}_job_v1.py
  value_objects/ios/{business_job}_input_v1.py
  value_objects/ios/{business_job}_output.py
  value_objects/events/
  repositories/
  exceptions/

backend/app/usecase/job/{area}/{business_job}_job_use_case.py

backend/app/infrastructure/arq/jobs/execute_{business_job}_job_use_case.py
```

### Job Domain Model

`Job` is the base entity for one persisted execution. It owns identity, type,
version, typed input/result, status, initiator, parent job id, timestamps, error,
and dispatch metadata.

`JobContract[InputT, ResultT]` is the executable domain entity base. Every
business job version inherits from it:

```python
class CodexRunJobV1(JobContract[CodexRunInputV1, CodexRunOutput]):
    type: Literal["execute_codex_run_job_use_case"] = "execute_codex_run_job_use_case"
    version: Literal["v1"] = "v1"
    input = CodexRunInputV1
    result = CodexRunOutput
```

Rules:

- Concrete job contracts are entities and live in `entities/`.
- Concrete job contracts inherit from `JobContract`, not from a value object.
- The `type` literal is the stable dispatch key and matches the ARQ executor
  function name.
- The `version` literal is part of the persisted contract identity.
- Job input/output dataclasses live in `value_objects/ios/`, one class per file.
- Events live in `value_objects/events/`, one event payload/event class pair per
  file.
- Job sessions, stored records, and other persisted lifecycle objects are
  entities, not value objects.
- Do not register job entities with decorators. The job registry discovers
  concrete `JobContract` subclasses from `app.domain` and keys them by
  `(type, version)`.

### Creating Jobs

Presentation constructs a typed pending job and sends it to the create-job use
case:

```python
job = CodexRunJobV1.new(
    initiator=Initiator.from_user(current_user),
    input=CodexRunInputV1(prompt=body.prompt, workdir=body.workdir),
    name="Codex run",
    description="Run Codex against a workspace",
)
await create_job.execute(job)
```

Rules:

- Create the typed job before calling the use case.
- Call `CreateJobUseCase.execute(job)`.
- The create-job use case only registers a `PENDING` job in durable storage.
- The create-job use case does not enqueue ARQ directly.
- Unknown `(type, version)` contracts fail before persistence.
- Non-`PENDING` jobs fail before persistence.

There is no separate job outbox for dispatch. `JobStatus.PENDING` is the durable
dispatch request.

### Dispatching Jobs

The ARQ worker process owns a cron job that calls the SQLModel job dispatcher.
The dispatcher:

1. Selects due `PENDING` jobs with `FOR UPDATE SKIP LOCKED`.
2. Finds a worker binding by persisted `(type, version)`.
3. Enqueues the ARQ function through `JobRuntime.enqueue(job_type, job_id)`.
4. Marks the job `QUEUED` when enqueue succeeds.
5. Stores retry metadata and backoff when enqueue fails.
6. Marks the job `FAILED` when no worker binding exists.

Rules:

- Dispatch is infrastructure.
- Dispatch is atomic at the database boundary.
- Dispatch never executes business logic.
- Dispatch uses `JobRuntime`; do not create separate queue/cancellation ports
  for new job flows.

### Worker Binding

Every executable job has one ARQ executor function:

```python
@job_worker
async def execute_codex_run_job_use_case(
    ctx: dict[str, Any],
    job: CodexRunJobV1,
) -> CodexRunOutput:
    storage = ctx[ARQ_FILE_STORAGE]
    use_case = new_codex_run_job_use_case(...)
    return await use_case.execute(job)
```

Rules:

- The executor file name is `execute_{business_job}_job_use_case.py`.
- The executor function name is the same as the job contract `type`.
- The function is decorated with `@job_worker`.
- The `job` parameter is annotated with the concrete job entity.
- The executor takes required infrastructure dependencies from ARQ `ctx` when
  needed.
- The executor manually composes the use case at the transport boundary.
- Do not pass a base `Job` into a business job use case.
- Do not pass `job_id` into a business job use case.
- The decorator infers the contract from the `job` annotation.
- The decorator claims `QUEUED -> RUNNING` before business execution.
- The decorator loads the persisted job and verifies its concrete contract type.
- The decorator writes terminal state:
  `SUCCEEDED`, `FAILED`, or `CANCELLED`.
- Business use cases return typed output and raise domain/application errors.
  They do not write generic job status transitions.

### Business Job Use Cases

Business job use cases execute domain/application work for one typed job:

```python
class CodexRunJobUseCase(ABC):
    async def execute(self, job: CodexRunJobV1) -> CodexRunOutput: ...
```

Rules:

- The public method is always `execute`.
- The input is the concrete job entity.
- The output is the concrete typed job output/result.
- Read job input directly through `job.input`.
- Append domain job events for meaningful business milestones.
- Attach files through `JobRepository.add_file`.
- Use `JobFile` for files associated with a job. `JobFile` inherits from the
  file domain `File` entity.
- Use domain exceptions for business failures.
- Let `asyncio.CancelledError` propagate after local cleanup so the worker
  binding can mark the job cancelled.
- Do not duplicate generic status handling in the business use case.

### Job Repository

`JobRepository` is the aggregate repository for job persistence. It owns the
job aggregate read/write surface:

- create/get/save/delete job entities;
- get `JobSummary` and `JobDetails`;
- add/list `JobFile`;
- append/list `JobEvent`;
- perform atomic status transitions:
  `try_mark_running`, `try_mark_succeeded`, `try_mark_failed`,
  `try_mark_cancelled`.

Rules:

- Keep job, job files, job events, summaries, details, and status transitions
  behind `JobRepository` unless a real aggregate boundary forces a split.
- Repository ports live in domain.
- SQLModel DTOs and repository implementations live in infrastructure.
- Payload serialization is infrastructure. Domain IO remains plain dataclasses;
  the SQLModel payload codec may adapt them for JSON persistence.

### Job Runtime

`JobRuntime` is the usecase port for the external execution system. It supports:

- enqueue persisted jobs;
- abort queued/running runtime jobs;
- request cooperative cancellation;
- check and clear cooperative cancellation markers;
- wait for a terminal runtime result with `await_terminal`.

ARQ implements this port. Redis, ARQ `Job.abort()`, queue names, result polling,
and cancellation markers stay in infrastructure.

Rules:

- Use `JobRuntime` for runtime operations.
- Do not inject raw ARQ/Redis into use cases.
- Do not add separate `JobQueue` or `JobCancellationBackend` ports.
- Long-running adapters should expose their own local `cancel()` operation
  when they need cleanup on `asyncio.CancelledError`.

### Cancelling Jobs

Cancellation is a use case, not route logic.

`CancelJobUseCase.execute(job_id, current_user_id=...)`:

1. Loads the job.
2. Checks ownership/access.
3. For `RUNNING`, writes a cooperative cancellation request and aborts the ARQ
   job through `JobRuntime.cancel`.
4. For `QUEUED`, aborts the ARQ job and marks the domain job cancelled.
5. For `PENDING`, marks the domain job cancelled without touching ARQ.
6. Rejects terminal or otherwise non-cancellable jobs with a domain exception.

Rules:

- Presentation passes `current_user_id` and maps domain exceptions to HTTP.
- Presentation does not read repositories to decide whether cancellation is
  allowed.
- Running jobs become `CANCELLED` through the worker binding when ARQ raises
  `asyncio.CancelledError`.
- Pending and queued jobs are marked cancelled directly by the cancel use case
  because no business executor may run.

### Job Status Lifecycle

The normal lifecycle is:

```text
PENDING -> QUEUED -> RUNNING -> SUCCEEDED
                         └──> FAILED
                         └──> CANCELLED

PENDING -> CANCELLED
QUEUED  -> CANCELLED
```

Rules:

- `PENDING` means persisted and waiting for dispatcher pickup.
- `QUEUED` means ARQ accepted the runtime job.
- `RUNNING` means the worker binding claimed execution.
- `SUCCEEDED` means the worker returned typed output and it was persisted.
- `FAILED` means dispatch failed permanently or business execution raised.
- `CANCELLED` means cancellation was accepted and persisted.
