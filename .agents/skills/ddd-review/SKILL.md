---
name: ddd-review
description: Use when reviewing backend DDD correctness, checking layer boundaries, validating entity/value object/repository placement, auditing job architecture, or running the repository's deterministic DDD linter.
---

# DDD Review Skill

Use before finalizing backend architecture changes and whenever the user asks
for review.

## Review Order

1. Name touched layers: domain, usecase, infrastructure, presentation, tests,
   tooling.
2. Check ownership: entity vs value object vs repository port vs usecase port
   vs DTO vs schema.
3. Check that every domain object lives in the correct domain folder.
4. Check that every use case receives domain objects/value objects and returns
   domain objects/value objects.
5. Check dependency direction.
6. Check exception convention and exception placement.
7. Check file placement and one-primary-class-per-file.
8. Check job conventions when job code is touched.
9. Check tests mirror source paths and use AAA.
10. Run deterministic checks.

## Mandatory Architecture Checks

Reviewers must verify these rules every time relevant files are touched:

- Domain entities live under `backend/app/domain/**/entities/`.
- Domain value objects live under `backend/app/domain/**/value_objects/`.
- Domain repository ports live under `backend/app/domain/**/repositories/`.
- Domain exceptions live under `backend/app/domain/**/exceptions/`.
- Infrastructure DTOs and repository implementations live under
  `backend/app/infrastructure/**`.
- Presentation schemas live under `backend/app/presentation/**/schemas/`.
- One primary class per file. Do not group several domain classes in one file
  because they are small.
- Event files may contain exactly one `*Payload` value object and exactly one
  event class when the event class has a `payload` field typed with that
  payload class.
- File names are snake_case versions of the primary class names.

Usecase contract rules:

- Use cases work with domain objects only.
- Usecase input is a domain entity/value object or primitives that are part of
  the application command boundary and immediately converted to domain.
- Usecase output is a domain entity/value object, typed domain result, or
  `None` for command-style actions.
- Use cases do not return DTOs, presentation schemas, SQLModel models, Redis
  records, ARQ jobs, or raw persistence payloads.
- Usecase ports may be defined next to a use case under
  `backend/app/usecase/**/ports/` when the port is for an external capability
  needed by that application workflow.
- Repository ports for persisted domain entities stay in domain
  `repositories/`, not usecase `ports/`.

Exception rules:

- Every domain exception is its own class in its own file.
- Exception files live in the owning domain `exceptions/` package.
- Every exception has a default `detail` or `message` string.
- Exceptions are re-exported from local `exceptions/__init__.py`.
- Public domain exceptions are re-exported from the domain package API.
- Presentation maps domain/usecase exceptions to HTTP; it does not define
  domain exceptions.

## Commands

Run the relevant subset, and run all before broad backend completion:

```bash
uv run ruff check backend
uv run ty check backend/app
uv run pytest backend/tests
uv run python backend/scripts/ddd_linter.py
```

## DDD Linter Policy

`backend/scripts/ddd_linter.py` is the executable architecture policy. It should cover
every convention that can be checked statically.

Required check categories:

- layer import direction;
- forbidden framework imports in domain;
- usecase not importing infrastructure or presentation;
- presentation not importing infrastructure repositories/adapters directly;
- entity files under `domain/**/entities/`;
- value object files under `domain/**/value_objects/`;
- exception files under `domain/**/exceptions/`;
- repository ports under `domain/**/repositories/`;
- repository implementations under `infrastructure/**`;
- DTOs under `infrastructure/**`;
- schemas under `presentation/**/schemas/`;
- one primary entity/value object/exception per file;
- exception class name matches file name;
- exception has default `detail` or `message`;
- exception package exports public exceptions;
- no dataclasses in usecase/presentation/infrastructure unless explicitly
  allowed DTO/test/helper context;
- tests mirror source paths;
- tests use AAA phase comments;
- `.agents/skills/` contains canonical skills;
- `.codex/skills/` contains symlinks to `.agents/skills/`;
- no root `skills/` directory.

Job-specific checks:

- concrete job contracts live in `domain/job/**/entities/`;
- concrete job contracts inherit from `JobContract`;
- job contracts define `type: Literal[...]` and `version: Literal[...]`;
- job contracts assign `input` and `result`;
- job IO lives only in `value_objects/ios/`;
- job events live only in `value_objects/events/`;
- job event payloads include `job_id`;
- event files with two dataclasses are allowed only for the strict
  `Payload + Event(payload: Payload)` pair;
- no job entity registration decorators;
- no `JobQueue`, `JobCancellationBackend`, or job outbox reintroduction;
- ARQ executors are named `execute_*_job_use_case`;
- ARQ executors use `@job_worker` without `contract=`;
- ARQ executor `job` parameter is annotated with a concrete job contract;
- business job usecases accept concrete job contracts, not `job_id` or base
  `Job`;
- business job usecases do not mutate generic lifecycle fields;
- generic lifecycle transitions stay in worker binding/repository/cancel flow.

The linter is intentionally strict. If it fails on existing debt, report the
violations separately from regressions introduced by the current change.

## Review Output

Findings come first, ordered by severity.

Each finding includes:

- file path;
- rule violated;
- why it matters;
- concrete fix.

Then include verification commands and residual risk.

If there are no findings, say that directly and still list any commands not
run.
