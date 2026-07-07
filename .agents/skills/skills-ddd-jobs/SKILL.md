---
name: skills-ddd-jobs
description: Use when changing job domain contracts, CreateJobUseCase, JobRepository, job dispatcher, ARQ workers, cancellation, Codex auth/run jobs, job events, job files, or job serialization.
---

# DDD Job Skill

Use this for any change under `domain/job`, `usecase/job`,
`infrastructure/arq`, `infrastructure/sqlmodel/job`, Codex job adapters, or job
routes.

## Job Lifecycle

1. Presentation receives an HTTP request and creates a typed domain job
   contract, for example `CodexAuthJobV1` or `CodexRunJobV1`.
2. `CreateJobUseCase` persists the already constructed domain `Job` with
   status `PENDING`. The pending job row itself is the durable dispatch intent.
3. ARQ worker settings register a cron job that calls `dispatch_pending_jobs`.
4. The job dispatcher selects due `PENDING` jobs, resolves the worker binding
   from job type/version, and enqueuees the ARQ worker.
5. After successful enqueue the dispatcher marks the job `QUEUED`; if enqueue
   fails, it keeps the job `PENDING` and stores retry metadata on the job row.
6. The `@job_worker` wrapper atomically claims `QUEUED -> RUNNING`, then the
   ARQ worker builds infrastructure dependencies and calls the dedicated
   business use case.
7. The business use case writes business-specific side effects: domain events,
   files, auth sessions, external executor/authenticator actions.
8. The `@job_worker` wrapper writes generic terminal lifecycle:
   `SUCCEEDED + result`, `FAILED + JobError`, or `CANCELLED + JobError`.
9. Cancellation updates durable job state and asks the ARQ cancellation backend
   to abort running queued work.

## Business Job Rules

- Each business job has a domain contract under
  `backend/app/domain/job/{job_name}_job_use_case`.
- The concrete job entity inherits from
  `JobContract[Input, Output]`, and `JobContract` inherits from `Job`.
- Each business job has a dedicated use case under
  `backend/app/usecase/job/{area}/{job_name}_job_use_case.py`.
- Job input/result/output are typed domain classes, not raw `dict`.
- Put only job IO classes in `value_objects/ios/`.
- Put business job events in `value_objects/events/`.
- `JobEventPayload` must include `job_id`; every emitted job event payload
  passes `job_id=job.id`.
- `JobFile` inherits from `File`; do not wrap a nested `file: File`.
- Immediate output returned by a job use case belongs to the domain contract if
  it is part of that business job's language.
- Since `execute(...)` receives the concrete job type, use typed fields
  directly, for example `job.input.prompt`. Do not re-parse `job.input` from a
  dict inside the business use case.
- Business job use cases must not mutate generic `Job` lifecycle fields
  (`status`, `result`, `error`, `started_at`, `finished_at`). That is shared
  `@job_worker` responsibility.
- Infrastructure serialization lives at infrastructure boundaries, for example
  SQLModel payload codecs.

## Codex Auth Job

- `CodexAuthSession` is a domain entity because it has identity (`job_id`),
  lifecycle status, and repository persistence.
- `CodexAuthSessionRepository` is a domain repository port.
- Redis implementation is infrastructure:
  `backend/app/infrastructure/codex/auth_session.py`.
- HTTP polling calls `CodexAuthUseCase.get_code_and_url(...)`; it is not a
  separate business job.

## ARQ Boundary Rules

- ARQ job functions are transport adapters.
- They may import infrastructure factories and domain job contracts.
- ARQ job functions must be decorated with `@job_worker`.
- `@job_worker` infers the contract from the annotated `job` parameter; do not
  pass `contract=`.
- They should return typed job outputs where ARQ needs a result.
- They must not contain business rules or state-machine ownership.
- Shared worker lifecycle checks belong in `@job_worker`, not in each concrete
  job function.
