"""Provide the use case for finding Codex device login sessions."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.agent.entities import CodexDeviceLoginSession
from app.usecase.agent.ports import CodexDeviceLoginGateway


class FindCodexDeviceLoginUseCase(ABC):
    """Define the application boundary for finding Codex device login sessions."""

    @abstractmethod
    async def execute(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Return a Codex device login session by ID."""


class FindCodexDeviceLoginUseCaseImpl(FindCodexDeviceLoginUseCase):
    """Find Codex device login sessions through a gateway abstraction."""

    def __init__(self, gateway: CodexDeviceLoginGateway):
        """Store use case dependencies."""
        self.gateway = gateway

    async def execute(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Return a Codex device login session by ID."""
        return await self.gateway.find_by_id(session_id)


def new_find_codex_device_login_use_case(
    gateway: CodexDeviceLoginGateway,
) -> FindCodexDeviceLoginUseCase:
    """Instantiate the find Codex device login use case."""
    return FindCodexDeviceLoginUseCaseImpl(gateway)
