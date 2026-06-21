"""Health-check API tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app

pytestmark = pytest.mark.anyio


async def test_health_check_returns_true() -> None:
    # Arrange
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Act
        response = await client.get(f"{settings.API_V1_STR}/utils/health-check/")

    # Assert
    assert response.status_code == 200
    assert response.json() is True
