"""Item API presentation tests."""

from collections.abc import AsyncGenerator
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.user.value_objects import EmailAddress
from app.infrastructure.di import get_session
from app.infrastructure.security import new_password_hasher
from app.infrastructure.sqlmodel.item import ItemDTO
from app.infrastructure.sqlmodel.user import UserDTO, new_user_repository
from app.main import app
from app.usecase.user import new_create_user_use_case

pytestmark = pytest.mark.anyio


@dataclass(frozen=True)
class ApiContext:
    """Authenticated API test context."""

    client: AsyncClient
    headers: dict[str, str]


async def _build_test_session() -> tuple[AsyncEngine, AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    assert UserDTO.__tablename__ == "user"
    assert ItemDTO.__tablename__ == "item"
    async with engine.begin() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)

    return engine, AsyncSession(engine)


async def _create_admin(session: AsyncSession) -> None:
    user_repository = new_user_repository(session)
    create_user = new_create_user_use_case(
        user_repository,
        new_password_hasher(),
    )
    await create_user.execute(
        email=EmailAddress("admin@example.com"),
        plain_password="password123",
        is_superuser=True,
    )
    await session.commit()


async def _login(client: AsyncClient) -> dict[str, str]:
    response = await client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": "admin@example.com", "password": "password123"},
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def api_context() -> AsyncGenerator[ApiContext]:
    """Yield an authenticated API test client."""
    engine, session = await _build_test_session()

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    try:
        await _create_admin(session)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            headers = await _login(client)
            yield ApiContext(client=client, headers=headers)
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await engine.dispose()


async def _create_item(api_context: ApiContext) -> dict[str, str]:
    response = await api_context.client.post(
        f"{settings.API_V1_STR}/items/",
        headers=api_context.headers,
        json={"title": "Item", "description": "Body"},
    )

    return response.json()


async def test_login_returns_access_token() -> None:
    # Arrange
    engine, session = await _build_test_session()

    async def override_get_session() -> AsyncGenerator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        await _create_admin(session)
        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            # Act
            response = await client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={"username": "admin@example.com", "password": "password123"},
            )
    finally:
        app.dependency_overrides.clear()
        await session.close()
        await engine.dispose()

    # Assert
    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_create_item_returns_created_item(api_context: ApiContext) -> None:
    # Act
    response = await api_context.client.post(
        f"{settings.API_V1_STR}/items/",
        headers=api_context.headers,
        json={"title": "Item", "description": "Body"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["title"] == "Item"
    assert response.json()["description"] == "Body"


async def test_list_items_returns_created_item(api_context: ApiContext) -> None:
    # Arrange
    await _create_item(api_context)

    # Act
    response = await api_context.client.get(
        f"{settings.API_V1_STR}/items/",
        headers=api_context.headers,
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["count"] == 1


async def test_update_item_returns_updated_item(api_context: ApiContext) -> None:
    # Arrange
    item = await _create_item(api_context)

    # Act
    response = await api_context.client.put(
        f"{settings.API_V1_STR}/items/{item['id']}",
        headers=api_context.headers,
        json={"title": "Updated"},
    )

    # Assert
    assert response.status_code == 200
    assert response.json()["title"] == "Updated"


async def test_delete_item_returns_success(api_context: ApiContext) -> None:
    # Arrange
    item = await _create_item(api_context)

    # Act
    response = await api_context.client.delete(
        f"{settings.API_V1_STR}/items/{item['id']}",
        headers=api_context.headers,
    )

    # Assert
    assert response.status_code == 200
