"""Item HTTP routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.domain.item.exceptions import ItemAccessDeniedError, ItemNotFoundError
from app.domain.item.value_objects import ItemDescription, ItemId, ItemTitle
from app.infrastructure.di import (
    get_create_item_use_case,
    get_delete_item_use_case,
    get_find_item_by_id_use_case,
    get_find_items_use_case,
    get_update_item_use_case,
)
from app.presentation.api.common import Message
from app.presentation.api.common.deps import CurrentUser
from app.presentation.api.item import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate
from app.usecase.item import (
    CreateItemUseCase,
    DeleteItemUseCase,
    FindItemByIdUseCase,
    FindItemsUseCase,
    UpdateItemUseCase,
)

router = APIRouter(prefix="/items", tags=["items"])


def _description(value: str | None) -> ItemDescription | None:
    """Build an optional item description value object."""
    return ItemDescription(value) if value is not None else None


def _map_item_error(error: Exception) -> HTTPException:
    """Map item domain errors to public HTTP responses."""
    if isinstance(error, ItemNotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    if isinstance(error, ItemAccessDeniedError):
        return HTTPException(status_code=403, detail=error.message)
    return HTTPException(status_code=500)


@router.get("/", response_model=ItemsPublic)
async def read_items(
    current_user: CurrentUser,
    use_case: Annotated[FindItemsUseCase, Depends(get_find_items_use_case)],
    skip: int = 0,
    limit: int = 100,
) -> ItemsPublic:
    """Retrieve items visible to the current user."""
    result = await use_case.execute(current_user, offset=skip, limit=limit)
    return ItemsPublic(
        data=[ItemPublic.from_entity(item) for item in result.data],
        count=result.count,
    )


@router.get("/{id}", response_model=ItemPublic)
async def read_item(
    current_user: CurrentUser,
    use_case: Annotated[FindItemByIdUseCase, Depends(get_find_item_by_id_use_case)],
    id: uuid.UUID,
) -> ItemPublic:
    """Get item by ID."""
    try:
        item = await use_case.execute(current_user, ItemId(id))
    except (ItemNotFoundError, ItemAccessDeniedError) as error:
        raise _map_item_error(error) from error
    return ItemPublic.from_entity(item)


@router.post("/", response_model=ItemPublic)
async def create_item(
    current_user: CurrentUser,
    use_case: Annotated[CreateItemUseCase, Depends(get_create_item_use_case)],
    item_in: ItemCreate,
) -> ItemPublic:
    """Create a new item."""
    try:
        item = await use_case.execute(
            current_user=current_user,
            title=ItemTitle(item_in.title),
            description=_description(item_in.description),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return ItemPublic.from_entity(item)


@router.put("/{id}", response_model=ItemPublic)
async def update_item(
    current_user: CurrentUser,
    use_case: Annotated[UpdateItemUseCase, Depends(get_update_item_use_case)],
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> ItemPublic:
    """Update an item."""
    try:
        item = await use_case.execute(
            current_user=current_user,
            item_id=ItemId(id),
            title=ItemTitle(item_in.title) if item_in.title is not None else None,
            description=_description(item_in.description),
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (ItemNotFoundError, ItemAccessDeniedError) as error:
        raise _map_item_error(error) from error
    return ItemPublic.from_entity(item)


@router.delete("/{id}")
async def delete_item(
    current_user: CurrentUser,
    use_case: Annotated[DeleteItemUseCase, Depends(get_delete_item_use_case)],
    id: uuid.UUID,
) -> Message:
    """Delete an item."""
    try:
        await use_case.execute(current_user, ItemId(id))
    except (ItemNotFoundError, ItemAccessDeniedError) as error:
        raise _map_item_error(error) from error
    return Message(message="Item deleted successfully")
