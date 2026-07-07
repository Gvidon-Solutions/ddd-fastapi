---
name: skills-ddd-presentation
description: Use when changing FastAPI routes, request/response schemas, current-user dependencies, dependency injection wiring, or mapping domain/usecase errors to HTTP responses in this repository.
---

# DDD Presentation Skill

Use for `backend/app/presentation` and FastAPI DI changes.

## Presentation Responsibilities

- Validate HTTP input shape.
- Convert transport primitives to domain/usecase inputs.
- Call usecase interfaces.
- Map domain/usecase exceptions to HTTP status codes.
- Convert domain/usecase outputs to response schemas.

## What Presentation Must Not Do

- No business state transitions.
- No repository orchestration except through DI providers.
- No SQLModel/Redis/ARQ access from routes.
- No domain dataclass definitions.

## DI Rules

- DI lives in `backend/app/infrastructure/di/injection.py`.
- DI may assemble infrastructure implementations and usecase factories.
- Routes depend on usecase interfaces and launcher/cancellation interfaces, not
  concrete infrastructure classes.

## Schema Rules

- Request/response schemas live under
  `backend/app/presentation/api/{area}/schemas`.
- Schemas are transport DTOs, not domain objects.
- Domain must never import presentation schemas.

## Route Checklist

1. Identify usecase dependency.
2. Validate request schema.
3. Call usecase.
4. Map expected errors.
5. Return response schema.
6. Add/adjust presentation tests under mirrored path.
