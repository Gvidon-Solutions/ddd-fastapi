"""Provide the use case for reading Codex CLI login status."""

from abc import ABC, abstractmethod

from app.domain.agent.entities import CodexLoginStatus
from app.usecase.agent.ports import CodexDeviceLoginGateway


class GetCodexLoginStatusUseCase(ABC):
    """Define the application boundary for Codex CLI login status."""

    @abstractmethod
    async def execute(self) -> CodexLoginStatus:
        """Return Codex CLI authentication status."""


class GetCodexLoginStatusUseCaseImpl(GetCodexLoginStatusUseCase):
    """Read Codex login status through a gateway abstraction."""

    def __init__(self, gateway: CodexDeviceLoginGateway):
        """Store use case dependencies."""
        self.gateway = gateway

    async def execute(self) -> CodexLoginStatus:
        """Return Codex CLI authentication status."""
        return await self.gateway.status()


def new_get_codex_login_status_use_case(
    gateway: CodexDeviceLoginGateway,
) -> GetCodexLoginStatusUseCase:
    """Instantiate the Codex login status use case."""
    return GetCodexLoginStatusUseCaseImpl(gateway)
