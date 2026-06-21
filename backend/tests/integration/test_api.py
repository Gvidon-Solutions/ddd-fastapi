"""FastAPI integration tests."""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings
from app.domain.user.value_objects import EmailAddress
from app.infrastructure.di import get_session
from app.infrastructure.security import new_password_hasher
from app.infrastructure.sqlmodel.item import ItemDTO
from app.infrastructure.sqlmodel.user import UserDTO, new_user_repository
from app.main import app
from app.usecase.user import new_create_user_use_case


def _build_test_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    assert UserDTO.__tablename__ == "user"
    assert ItemDTO.__tablename__ == "item"
    SQLModel.metadata.create_all(engine)
    session = Session(engine)

    return session


def test_health_check() -> None:
    with TestClient(app) as client:
        response = client.get(f"{settings.API_V1_STR}/utils/health-check/")

    assert response.status_code == 200
    assert response.json() is True


def test_login_and_item_crud_flow() -> None:
    session = _build_test_session()

    def override_get_session() -> Generator[Session]:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    app.dependency_overrides[get_session] = override_get_session
    try:
        user_repository = new_user_repository(session)
        create_user = new_create_user_use_case(
            user_repository,
            new_password_hasher(),
        )
        create_user.execute(
            email=EmailAddress("admin@example.com"),
            plain_password="password123",
            is_superuser=True,
        )
        session.commit()

        with TestClient(app) as client:
            login_response = client.post(
                f"{settings.API_V1_STR}/login/access-token",
                data={"username": "admin@example.com", "password": "password123"},
            )
            assert login_response.status_code == 200
            headers = {
                "Authorization": f"Bearer {login_response.json()['access_token']}"
            }

            create_response = client.post(
                f"{settings.API_V1_STR}/items/",
                headers=headers,
                json={"title": "Item", "description": "Body"},
            )
            assert create_response.status_code == 200
            item_id = create_response.json()["id"]

            list_response = client.get(
                f"{settings.API_V1_STR}/items/",
                headers=headers,
            )
            assert list_response.status_code == 200
            assert list_response.json()["count"] == 1

            update_response = client.put(
                f"{settings.API_V1_STR}/items/{item_id}",
                headers=headers,
                json={"title": "Updated"},
            )
            assert update_response.status_code == 200
            assert update_response.json()["title"] == "Updated"

            delete_response = client.delete(
                f"{settings.API_V1_STR}/items/{item_id}",
                headers=headers,
            )
            assert delete_response.status_code == 200
    finally:
        app.dependency_overrides.clear()
        session.close()
