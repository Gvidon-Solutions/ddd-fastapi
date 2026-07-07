---
name: ddd-jobs
description: Use when changing job domain contracts, CreateJobUseCase, JobRepository, job dispatcher, ARQ workers, cancellation, Codex auth/run jobs, job events, job files, or job serialization.
---

# DDD Job Skill

Use for changes under `domain/job`, `usecase/job`, `infrastructure/arq`,
`infrastructure/sqlmodel/job`, Codex job adapters, job routes, and job tests.

## Core Rule

A job is a durable typed domain entity. It is not an ARQ function, not a raw
dict payload, and not a transport DTO.

Start with the domain contract, then wire persistence, dispatcher, runtime, and
presentation.

## Job Lifecycle

1. Presentation creates a concrete typed `JobContract`, for example
   `CodexAuthJobV1` or `CodexRunJobV1`.
2. `CreateJobUseCase.execute(job)` persists the already constructed job with
   status `PENDING`.
3. `PENDING` is the durable dispatch request. There is no separate job outbox.
4. ARQ worker settings register a cron job that calls `dispatch_pending_jobs`.
5. The dispatcher selects due `PENDING` rows with locking, resolves worker
   binding from `(type, version)`, and calls `JobRuntime.enqueue(...)`.
6. Successful enqueue marks the job `QUEUED`.
7. `@job_worker` atomically claims `QUEUED -> RUNNING`.
8. `@job_worker` loads the persisted job and verifies the concrete contract
   from the annotated `job` parameter.
9. The ARQ executor pulls needed dependencies from `ctx`, manually composes the
   use case, and calls `use_case.execute(job)`.
10. The business use case writes business side effects: events, files,
    sessions, and external adapter calls.
11. `@job_worker` writes generic terminal lifecycle:
    `SUCCEEDED + result`, `FAILED + JobError`, or `CANCELLED + JobError`.

## Business Job Contract

Each business job has a domain package:

```text
backend/app/domain/job/{job_name}_job_use_case/
  entities/{job_name}_job_v1.py
  value_objects/ios/{job_name}_input_v1.py
  value_objects/ios/{job_name}_output.py
  value_objects/events/
  repositories/
  exceptions/
```

Rules:

- The concrete job entity inherits from `JobContract[Input, Output]`.
- `JobContract` inherits from `Job`.
- The job entity defines `type: Literal["execute_{name}_job_use_case"]`.
- The job entity defines `version: Literal["v1"]`.
- The job entity assigns `input = InputClass` and `result = OutputClass`.
- Job input/output are typed domain dataclasses, not raw `dict`.
- Put only job IO classes in `value_objects/ios/`.
- Put business job events in `value_objects/events/`.
- A job event file may contain one event payload value object and one event
  class when the event class has `payload: ThatPayload`.
- Put job-specific persisted lifecycle objects in `entities/`, not
  `value_objects/`.
- Domain job contracts are discovered by registry. Do not decorate job
  entities for registration.

## Business Job Use Case

Each business job has one application use case:

```text
backend/app/usecase/job/{area}/{job_name}_job_use_case.py
```

The interface exposes:

```python
async def execute(self, job: ConcreteJobV1) -> Output: ...
```

Rules:

- Accept the concrete job entity, not `job_id` and not base `Job`.
- Use typed fields directly: `job.input.prompt`, `job.input.workdir`, etc.
- Do not re-parse `job.input` from `dict`.
- Do not defensively check the contract type inside business logic.
- Write business events with `payload.job_id`.
- Add job files as `JobFile`, not as nested `File` containers.
- Use job-specific domain repositories for job-owned entities.
- Use external usecase ports for external systems.
- Raise domain exceptions for business failures.
- Let `asyncio.CancelledError` propagate after local adapter cleanup.
- Do not mutate generic lifecycle fields: `status`, `result`, `error`,
  `started_at`, `finished_at`.

## ARQ Executor

Every executable job has one ARQ executor:

```text
backend/app/infrastructure/arq/jobs/execute_{name}_job_use_case.py
```

Shape:

```python
@job_worker
async def execute_example_job_use_case(
    ctx: dict[str, Any],
    job: ExampleJobV1,
) -> ExampleOutput:
    dependency = ctx[SOME_ARQ_CONTEXT_KEY]
    use_case = new_example_job_use_case(...)
    return await use_case.execute(job)
```

Rules:

- Function name equals the job contract `type`.
- Decorate with `@job_worker`.
- Annotate `job` with the concrete job entity.
- Do not pass `contract=` to `@job_worker`.
- Pull required infrastructure dependencies from ARQ `ctx` when needed.
- Manually compose the use case at this transport boundary.
- Do not claim execution, mark running, mark succeeded, mark failed, or mark
  cancelled in the executor body.
- Do not serialize results manually.

## Job Repository

Use the single domain `JobRepository` for the job aggregate:

- create/get/save/delete jobs;
- summaries/details;
- job files;
- job events;
- atomic lifecycle transitions;
- typed payload persistence through infrastructure codecs.

Do not add separate job query/file/event repositories unless a real aggregate
boundary is deliberately introduced and documented.

## Job Runtime

`JobRuntime` is the single usecase port for runtime execution:

- `enqueue`;
- `cancel`;
- `request_cancel`;
- `is_cancel_requested`;
- `clear_cancel_request`;
- `await_terminal`.

ARQ implements `JobRuntime`.

Rules:

- Do not inject raw ARQ or Redis into use cases.
- Do not reintroduce `JobQueue`.
- Do not reintroduce `JobCancellationBackend`.
- Cancellation routes call `CancelJobUseCase`, not runtime adapters directly.

## Codex Auth Job

- `CodexAuthSession` is a domain entity because it has identity (`job_id`),
  lifecycle status, and repository persistence.
- `CodexAuthSessionRepository` is a domain repository port.
- Redis implementation is infrastructure:
  `backend/app/infrastructure/codex/auth_session.py`.
- HTTP polling for auth code is a separate use case, not a method hidden inside
  the business auth job executor.

## Required Tests

For every new business job, add/update tests for:

- domain contract `.new(...)` and typed IO;
- business use case behavior with fake ports;
- emitted events include `payload.job_id`;
- files are `JobFile` objects;
- ARQ worker binding infers contract from the annotated `job` parameter;
- SQLModel round trip for typed `input`, `result`, event payloads, and files
  when persistence behavior changes;
- presentation launch route when the job is launched from HTTP.
