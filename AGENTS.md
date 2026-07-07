# Project Agent Rules

This backend follows Domain-Driven Design and Onion Architecture. These rules
are project law for AI agents and human reviewers.

## Required Skills

Before changing code, decompose the request by layer and use the matching
repo-local skill:

- `.agents/skills/ddd-architecture/SKILL.md` - domain, entities, value
  objects, repositories, exceptions, use cases, and layer boundaries.
- `.agents/skills/ddd-jobs/SKILL.md` - job contracts, launch flow,
  dispatcher, ARQ workers, cancellation, events, files, and Codex business jobs.
- `.agents/skills/ddd-presentation/SKILL.md` - FastAPI routes, schemas,
  DI, and exception-to-HTTP mapping.
- `.agents/skills/ddd-testing/SKILL.md` - test placement, mirrored structure,
  and Arrange / Act / Assert conventions.
- `.agents/skills/ddd-review/SKILL.md` - architectural review and
  deterministic `tools/ddd_linter.py` checks.

The canonical skill content lives under `.agents/skills/`. `.codex/skills/`
contains symlinks to those canonical skill directories.

## Request Decomposition

For every non-trivial task, identify which of these surfaces are touched:

- Domain: entities, value objects, domain events, repository ports, domain
  exceptions, job contracts.
- Use case: application workflow orchestration, ports that are not domain
  repositories, transaction boundaries.
- Infrastructure: SQLModel DTOs, repository implementations, Redis, ARQ,
  file storage, external CLIs, serialization adapters.
- Presentation: FastAPI routes, request/response schemas, auth dependencies,
  exception mapping.
- Tests: the test path must mirror the source path being tested.
- Tooling: DDD linter, typing, ruff, pytest, scripts, launchers.

Do not start edits until the affected layers and ownership are clear.

## Layer Rules

- Domain is the center. It must not import `app.usecase`,
  `app.infrastructure`, `app.presentation`, FastAPI, SQLModel, SQLAlchemy,
  Redis, ARQ, Pydantic schemas, or DTOs.
- Use case may import domain and usecase ports. It must not import
  infrastructure implementations or presentation schemas.
- Infrastructure implements domain repository ports and usecase ports. It owns
  SQLModel DTOs, Redis/ARQ adapters, file-system adapters, and codec helpers.
- Presentation owns HTTP transport concerns only. It validates transport input,
  calls use cases, maps exceptions to HTTP, and returns schemas.
- Tests mirror the source tree and make the target of each test obvious from
  the path.

## Domain Modeling Rules

- Entity: identity plus lifecycle/state transitions. Mutable dataclass is
  allowed. Entity files live under `domain/**/entities/{name}.py`.
- Value object: immutable value equality. Use `@dataclass(frozen=True)` or
  `StrEnum`. Value object files live under
  `domain/**/value_objects/{name}.py`.
- Repository port: domain contract for persisting/loading entities or
  aggregate read/query objects. Repository ports live under
  `domain/**/repositories/{name}_repository.py`.
- Repository implementation: infrastructure adapter only. It must live under
  `infrastructure/**` and implement a domain repository port.
- Exception: one exception class per file under `domain/**/exceptions/`.
  Exceptions must be exported from that package `__init__.py`.
- One primary domain class per file. Do not group entities/value objects just
  because they are small.

## Job Rules

Jobs are durable executions of typed domain contracts. Do not introduce a job
as an ARQ function first. Start from the domain contract, then wire transport.

### Job Model

- `Job[InputT, ResultT]` is the generic execution entity.
- `JobContract[InputT, ResultT]` inherits from `Job` and defines the durable
  `(type, version)` contract plus `input` and `result` classes.
- A concrete business job, for example `CodexRunJobV1`, inherits from
  `JobContract[CodexRunInputV1, CodexRunOutput]`.
- `JobSummary` and `JobDetails` are read-side value objects. `JobDetails`
  extends `JobSummary`; `Job` does not extend read-side objects.
- `JobFile` inherits from `File` and adds job-specific attachment metadata:
  `job_id`, `role`, `description`, `attached_at`.
- `JobEventPayload` must include `job_id`. Every business job event payload
  inherits from it and carries the job identity.

### Adding A New Business Job

1. Create a domain package:

   ```text
   backend/app/domain/job/{name}_job_use_case/
   ```

   It must contain `entities/`, `value_objects/ios/`,
   `value_objects/events/` when the job emits business events, and
   `repositories/` only if the job owns additional persisted domain entities.

2. Create exactly one entity file per job contract version:

   ```text
   entities/{name}_job_v1.py
   ```

   The class must inherit from `JobContract[Input, Output]`, define
   `type: Literal["execute_{name}_job_use_case"]`, `version: Literal["v1"]`,
   `input = {Name}InputV1`, and `result = {Name}Output`.

3. Put only job IO classes in `value_objects/ios/`.

   - Input file: `{name}_input_v1.py`.
   - Output/result file: `{name}_output.py` or a domain-specific result name.
   - IO classes are frozen dataclasses.
   - Do not put sessions, events, statuses, repositories, or random helper
     value objects in `ios/`.

4. Put business events in `value_objects/events/`.

   - One event class per file.
   - Event payload inherits from `JobEventPayload` and requires `job_id`.
   - Event class inherits from `JobEvent`.
   - Event `type` is a stable `Literal`, for example `CodexRunSucceededV1`.
   - Event `source` is the business use case name, for example
     `codex_run_job_use_case`.

5. Add the application use case under:

   ```text
   backend/app/usecase/job/{area}/{name}_job_use_case.py
   ```

   The interface must expose `execute(self, job: ConcreteJobV1) -> Output`.
   Since the job argument is typed, use the typed contract directly:
   `job.input.prompt`, `job.input.workdir`, etc. Do not re-parse `job.input`
   from `dict` and do not add defensive contract checks inside the business
   use case.

6. Business use cases may write business-specific side effects:

   - `jobs.append_event(job.id, EventX(... payload=... job_id=job.id ...))`;
   - `jobs.add_file(JobFile(... job_id=job.id ...))`;
   - job-specific domain repositories, such as auth sessions;
   - external usecase ports, such as Codex executor/authenticator.

   They must not mutate generic lifecycle fields:
   `status`, `result`, `error`, `started_at`, `finished_at`.

7. Register the ARQ boundary under:

   ```text
   backend/app/infrastructure/arq/jobs/execute_{name}_job_use_case.py
   ```

   The ARQ function must be decorated with `@job_worker` and annotate the job
   argument with the concrete contract:

   ```python
   @job_worker
   async def execute_example_job_use_case(
       ctx: dict[str, Any],
       job: ExampleJobV1,
   ) -> ExampleOutput:
       ...
   ```

   Do not pass `contract=` to the decorator. The decorator reads the contract
   from the `job` annotation.

8. ARQ worker functions are transport adapters only.

   They assemble infrastructure dependencies, instantiate the use case, and
   call `use_case.execute(job)`. They do not claim jobs, validate job type,
   write lifecycle status, catch business errors as domain decisions, or
   serialize results manually.

9. Launching a job means constructing the typed job first, then executing
   `CreateJobUseCase`:

   ```python
   job = ExampleJobV1.new(
       initiator=initiator,
       input=ExampleInputV1(...),
       name="Example",
   )
   await create_job.execute(job)
   ```

   `CreateJobUseCase` only registers durable pending jobs. It rejects unknown
   contracts and non-`PENDING` jobs with domain exceptions.

### Runtime Flow

1. Presentation creates a concrete `JobContract` instance with `.new(...)`.
2. `CreateJobUseCase.execute(job)` persists it as `PENDING`.
3. ARQ cron calls `dispatch_pending_jobs`.
4. The dispatcher picks due `PENDING` rows, resolves the worker binding from
   `(type, version)`, enqueuees ARQ work, then marks the job `QUEUED`.
5. `@job_worker` atomically claims `QUEUED -> RUNNING`.
6. `@job_worker` loads the persisted job and verifies it is the concrete
   annotated contract type.
7. The ARQ function builds infrastructure dependencies and calls the business
   use case.
8. The business use case performs business work and writes business events,
   files, and job-specific entities.
9. `@job_worker` writes the generic terminal state:
   `SUCCEEDED + result`, `FAILED + JobError`, or `CANCELLED + JobError`.

### Repository And Serialization Rules

- Use the single domain `JobRepository` for job persistence, read details,
  files, events, lifecycle transitions, and deletion.
- Do not add separate job query/file/event repositories unless the aggregate
  boundary is deliberately split and documented.
- SQLModel repositories are infrastructure implementations only.
- Job IO and event payload serialization belongs in infrastructure codecs.
- Persisted `input`, `result`, and event `payload` are JSON-compatible records;
  repository reads should hydrate typed dataclasses when the contract/event is
  known and fall back without losing data when it is unknown.
- Do not call `.to_dict()` at ARQ or presentation boundaries to fake typing.

### Required Job Tests

For every new business job, add or update tests for:

- domain contract `.new(...)` and typed IO;
- use case business behavior with a fake `JobRepository`;
- emitted events include `payload.job_id`;
- files are `JobFile` objects, not nested `File` containers;
- ARQ worker binding infers the contract from the annotated `job` parameter;
- SQLModel round trip for typed `input`, `result`, event payloads, and files
  when persistence behavior changes;
- presentation route, if the job is launched from HTTP.

## Quality Gates

Run these after relevant changes:

```bash
uv run ruff check backend
uv run ty check backend/app
uv run pytest backend/tests
uv run python tools/ddd_linter.py
```

`tools/ddd_linter.py` is intentionally stricter than the current codebase. If
it reports existing debt, either fix the debt in the same task or document the
remaining violations in the final response.
