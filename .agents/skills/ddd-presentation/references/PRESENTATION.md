# FastAPI Presentation Patterns

This reference adapts the `python-fastapi-ddd-presentation-skill` patterns to
this repository.

## Responsibilities

Presentation owns HTTP transport:

- parse path/query/body/header/current-user input;
- convert primitives to domain/usecase input;
- call `use_case.execute(...)`;
- map expected domain/usecase exceptions to HTTP responses;
- return response schemas.

Presentation does not own business rules. If a route needs to know whether a
job can be cancelled, a file can be read, or a user can access a resource, that
decision belongs in a use case unless it is purely authentication middleware.

## Route Template

```python
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.domain.some_area import SomeAccessDeniedError, SomeNotFoundError
from app.infrastructure.di import get_some_use_case
from app.presentation.api.common.deps import CurrentUser
from app.presentation.api.some_area import SomePublic
from app.usecase.some_area import SomeUseCase

router = APIRouter(prefix="/some-area", tags=["some-area"])


@router.get("/{item_id}", response_model=SomePublic)
async def get_item(
    current_user: CurrentUser,
    item_id: UUID,
    use_case: SomeUseCase = Depends(get_some_use_case),
) -> SomePublic:
    try:
        item = await use_case.execute(
            item_id=item_id,
            current_user_id=str(current_user.id),
        )
    except SomeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=exc.detail,
        ) from exc
    except SomeAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.detail,
        ) from exc

    return SomePublic.from_domain(item)
```

## Dependency Rules

Usecase dependencies use plain FastAPI default dependency syntax:

```python
use_case: SomeUseCase = Depends(get_some_use_case)
```

`CurrentUser` may stay as the existing alias. Do not convert usecase
dependencies to `Annotated[..., Depends(...)]` in this codebase.

## Schema Rules

Request schemas:

- validate JSON shape and transport constraints;
- do not replace domain invariants;
- live under `backend/app/presentation/api/{area}/schemas`.

Response schemas:

- expose public API fields only;
- convert UUID, datetime, enums, and domain values explicitly;
- use `from_domain(...)`, `from_entity(...)`, or direct construction when the
  route output is already simple.

## Error Mapping

Catch only expected exceptions:

```python
try:
    result = await use_case.execute(...)
except DomainNotFoundError as exc:
    raise HTTPException(status_code=404, detail=exc.detail) from exc
```

Do not catch broad `Exception` in route handlers.

## Common Violations

- Route reads `JobRepository` to check ownership before calling
  `CancelJobUseCase`.
- Route calls ARQ/Redis/file storage directly.
- Route mutates domain entity status.
- Route returns SQLModel DTOs.
- Route defines a dataclass or domain exception.
- Route maps an unexpected infrastructure failure as a business response.
