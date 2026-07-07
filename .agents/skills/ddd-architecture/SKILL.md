---
name: ddd-architecture
description: Use when changing backend architecture, domain models, entities, value objects, repository ports, exceptions, use cases, ports, DTO boundaries, or any code that may affect DDD/Onion Architecture layering in this repository.
---

# DDD Architecture Skill

Use before backend edits that touch domain, use cases, repositories, DTOs,
ports, exceptions, serialization, dependency injection, or cross-layer imports.

This repository follows FastAPI + Python DDD with Onion Architecture, adapted
from `dddpy` and `python-fastapi-ddd-skill`.

## Core Rule

Dependencies point inward only:

```text
Presentation -> UseCase -> Infrastructure -> Domain
```

The domain layer is the center and must stay pure. Inner layers do not import
outer layers.

## Workflow

1. Decompose the request by layer: domain, usecase, infrastructure,
   presentation, tests, tooling.
2. Identify the owner of every class/function being added or moved.
3. Choose the narrowest layer that owns the concept.
4. Check existing local patterns before adding abstractions.
5. Keep edits scoped to the requested behavior.
6. After edits, run `uv run python backend/scripts/ddd_linter.py` or explain why the
   task intentionally leaves violations.

## Layers

| Layer | Owns | Must Not Own |
| --- | --- | --- |
| `backend/app/domain` | Entities, value objects, domain events, repository ports, domain exceptions, job contracts | FastAPI, SQLModel, SQLAlchemy, Redis, ARQ, Pydantic schemas, DTOs, usecase ports |
| `backend/app/usecase` | Application workflows, usecase interfaces/implementations, factories, non-domain external ports | Domain dataclasses, entities, value objects, HTTP schemas, infrastructure implementations |
| `backend/app/infrastructure` | Adapter implementations: SQLModel DTOs, repositories, Redis, ARQ, file storage, external CLIs, codecs | Business rules, transport schemas |
| `backend/app/presentation` | FastAPI routes, request/response schemas, auth/current-user deps, exception-to-HTTP mapping | Business decisions, repository reads for usecase rules |

## Directory Layout

Backend code is laid out exactly like this:

```text
backend/app/domain/{area}/
  entities/
  value_objects/
  repositories/
  exceptions/

backend/app/usecase/{area}/
  {action}_{area}_use_case.py
  ports/

backend/app/infrastructure/{adapter}/{area}/
  *_dto.py
  *_repository.py

backend/app/presentation/api/{area}/
  routes/
  schemas/
```

Aggregates and subaggregates are allowed. Put them under the owning domain area
and keep the same internal shape:

```text
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

## Entities

Entity means identity plus lifecycle. If an object is saved, loaded, mutated by
identity, statused, or has repository persistence, model it as an entity.

Rules:

- Entity files live under `domain/**/entities/{name}.py`.
- One primary entity class per file.
- Entity identity is explicit (`id`, `file_id`, `job_id`, etc.).
- Equality should be identity-based when custom equality is needed.
- State transitions with business meaning belong on the entity or in a use
  case, not in presentation or infrastructure.
- Entities must not know about DTOs, SQLModel, FastAPI, Redis, or ARQ.

Use dataclasses when they fit the local model. Mutable dataclasses are allowed
for entities with lifecycle state.

## Value Objects

Value object means immutable value equality. It has no identity, no lifecycle,
and no repository.

Rules:

- Value object files live under `domain/**/value_objects/{name}.py`.
- One primary value object per file.
- Use `@dataclass(frozen=True)` or `StrEnum`.
- Validate local invariants in `__post_init__` when needed.
- Operations on value objects return new instances.
- Do not create repositories for value objects.
- Do not use value objects as a hiding place for entities, sessions, or
  persisted records.

## Repository Ports

Repository ports are domain contracts for loading and persisting domain
entities or aggregate read objects.

Rules:

- Repository ports live under `domain/**/repositories/{name}_repository.py`.
- Implementations live under `infrastructure/**`.
- Repository implementations convert DTOs to/from domain entities.
- Session lifecycle is managed by DI/transaction boundary, not by the domain.
- Do not place repository interfaces in `usecase` when they persist domain
  entities.
- Prefer one aggregate repository when callers need aggregate behavior
  together. Split repositories only for real aggregate boundaries, not because
  tables are separate.

## Use Cases

Use cases are application services. They orchestrate domain objects and ports
to perform one application action.

Required structure:

```python
class CreateThingUseCase(ABC):
    @abstractmethod
    async def execute(self, ...) -> Thing: ...


class CreateThingUseCaseImpl(CreateThingUseCase):
    ...


def new_create_thing_use_case(...) -> CreateThingUseCase:
    return CreateThingUseCaseImpl(...)
```

Rules:

- One use case per application action.
- Use case interface exposes one public `execute(...)` method.
- Use cases receive domain objects/value objects and return domain
  objects/value objects or typed domain results.
- Use cases never receive or return DTOs, presentation schemas, SQLModel
  models, Redis records, ARQ jobs, or raw persistence payloads.
- Use cases raise domain exceptions for business failures.
- Use cases may perform access checks and ownership rules when those rules
  affect the action.
- Usecase-local ports are allowed under `backend/app/usecase/**/ports/` for
  external capabilities needed by an application workflow.
- Repository ports for persisted domain entities stay in domain
  `repositories/`, not usecase `ports/`.
- Presentation must not duplicate usecase business checks by reading
  repositories directly.
- Factory functions are named `new_*_use_case`.

## Infrastructure DTOs

DTOs are infrastructure details that bridge persistence and domain models.

Rules:

- DTOs live under `backend/app/infrastructure/**`.
- DTOs may import domain classes for `to_entity()` / `from_entity()`.
- Domain classes must not import DTOs.
- Structured domain values should use explicit columns when the shape is
  stable. Use JSON only for deliberately open-ended metadata/payloads.
- Serialization codecs belong in infrastructure boundaries.

## Presentation

Presentation is transport only.

Rules:

- Routes construct domain value objects from request schemas.
- Routes call use cases.
- Routes map domain exceptions to HTTP status codes.
- Routes return response schemas.
- Routes do not read repositories to make business decisions that belong to a
  use case.
- Use FastAPI dependencies with `param: Type = Depends(provider)` for usecase
  dependencies. Existing `CurrentUser` alias is allowed.

## Exceptions

Domain exceptions are domain types.

Rules:

- One exception class per file under `domain/**/exceptions/`.
- Each exception has a default `detail` or `message` string.
- Use a small base exception per concern when useful, for example
  `JobCancelError`.
- Re-export exceptions from the local `exceptions/__init__.py` and the domain
  package `__init__.py` when they are part of the public domain API.
- Presentation catches domain exceptions and maps them to HTTP.

## File Rules

- One primary entity/value object/exception per file.
- Event files may contain one `*Payload` value object and one event class when
  the event class has a `payload` field typed with that payload class.
- File name is snake_case of the class name.
- Re-export public domain types from package `__init__.py` only after checking
  import cycles.
- Avoid low-level barrel exports if they create entity/value object cycles.

## References

Read these local references when more detail is needed:

- `.agents/skills/ddd-architecture/references/ARCHITECTURE.md`
- `.agents/skills/ddd-architecture/references/ENTITIES.md`
- `.agents/skills/ddd-architecture/references/VALUE_OBJECTS.md`
- `.agents/skills/ddd-architecture/references/REPOSITORIES.md`
- `.agents/skills/ddd-architecture/references/USECASES.md`

Also useful:

- `sources/dddpy/AGENTS.md`
- `sources/dddpy/README.md`
