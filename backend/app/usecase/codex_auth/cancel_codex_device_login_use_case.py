"""Provide the use case for cancelling Codex device login."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.codex_auth.entities import CodexDeviceLoginSession
from app.usecase.codex_auth.ports import CodexDeviceLoginGateway


class CancelCodexDeviceLoginUseCase(ABC):
    """Define the application boundary for cancelling Codex device login."""

    @abstractmethod
    async def execute(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Cancel and return a Codex device login session."""


class CancelCodexDeviceLoginUseCaseImpl(CancelCodexDeviceLoginUseCase):
    """Cancel Codex device login through a gateway abstraction."""

    def __init__(self, gateway: CodexDeviceLoginGateway):
        """Store use case dependencies."""
        self.gateway = gateway

    async def execute(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Cancel and return a Codex device login session."""
        return await self.gateway.cancel(session_id)


def new_cancel_codex_device_login_use_case(
    gateway: CodexDeviceLoginGateway,
) -> CancelCodexDeviceLoginUseCase:
    """Instantiate the cancel Codex device login use case."""
    return CancelCodexDeviceLoginUseCaseImpl(gateway)
