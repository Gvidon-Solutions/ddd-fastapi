---
name: ddd-presentation
description: Use when changing FastAPI routes, request/response schemas, current-user dependencies, dependency injection wiring, or mapping domain/usecase errors to HTTP responses in this repository.
---

# DDD Presentation Skill

Use for changes under `backend/app/presentation` and FastAPI dependency
wiring that affects presentation entrypoints.

## Layer Rule

Presentation is transport only. It may depend on domain and usecase types. It
must not own business decisions, persistence, ARQ, Redis, SQLModel sessions, or
domain dataclasses.

## Directory Layout

Presentation code is laid out like this:

```text
backend/app/presentation/api/{area}/
  routes/
  schemas/
```

Rules:

- Route functions live under `routes/`.
- Request and response schemas live under `schemas/`.
- Route modules may import usecase interfaces and DI providers.
- Route modules may import domain value objects/entities needed to construct
  usecase input.
- Domain and usecase layers never import presentation schemas.

## Route Rules

Each route does exactly this:

1. Accept transport input: path/query/body/current user/dependencies.
2. Convert transport primitives into domain/usecase inputs.
3. Call one usecase `execute(...)`.
4. Catch expected domain/usecase exceptions.
5. Map those exceptions to `HTTPException` or response status.
6. Convert usecase output into a response schema.

Routes must not:

- read repositories to decide whether an action is allowed;
- perform business state transitions;
- call SQLModel/Redis/ARQ/file storage directly;
- construct infrastructure adapters;
- catch broad `Exception` as business flow;
- define domain dataclasses or domain exceptions.

## Dependency Injection

Use this style for usecase dependencies:

```python
use_case: SomeUseCase = Depends(get_some_use_case)
```

Rules:

- Existing `CurrentUser` aliases are allowed.
- Do not use `Annotated[..., Depends(...)]` for usecase dependencies in this
  repository.
- DI providers live in `backend/app/infrastructure/di/injection.py`.
- DI providers assemble infrastructure implementations and usecase factories.
- Routes depend on usecase interfaces, not concrete infrastructure classes.

## Schemas

Schemas are transport DTOs.

Rules:

- Request schemas validate HTTP shape and basic transport constraints.
- Response schemas serialize domain/usecase output to JSON-friendly values.
- Keep schema conversion explicit.
- Do not return SQLModel DTOs or ORM models from routes.
- Do not rely on Pydantic schema validation as the only domain invariant
  enforcement.

## Error Mapping

Presentation maps expected domain/usecase exceptions to HTTP:

- not found -> `404`;
- access denied -> `403`;
- invalid command/state -> `400` or `409`;
- not ready / no content -> `204` when the route contract says so.

Unexpected exceptions are not business responses. Let framework middleware
handle them.

## Tests

Presentation tests mirror route paths and verify:

- request/response schema behavior;
- dependency overrides;
- usecase call shape;
- exception-to-HTTP mapping;
- access/current-user transport wiring.

Read `references/PRESENTATION.md` for templates and examples.
