"""Provide the use case for starting Codex device login."""

from abc import ABC, abstractmethod

from app.domain.agent.entities import CodexDeviceLoginSession
from app.usecase.agent.ports import CodexDeviceLoginGateway


class StartCodexDeviceLoginUseCase(ABC):
    """Define the application boundary for starting Codex device login."""

    @abstractmethod
    async def execute(self) -> CodexDeviceLoginSession:
        """Start and return a Codex device login session."""


class StartCodexDeviceLoginUseCaseImpl(StartCodexDeviceLoginUseCase):
    """Start Codex device login through a gateway abstraction."""

    def __init__(self, gateway: CodexDeviceLoginGateway):
        """Store use case dependencies."""
        self.gateway = gateway

    async def execute(self) -> CodexDeviceLoginSession:
        """Start and return a Codex device login session."""
        return await self.gateway.start()


def new_start_codex_device_login_use_case(
    gateway: CodexDeviceLoginGateway,
) -> StartCodexDeviceLoginUseCase:
    """Instantiate the start Codex device login use case."""
    return StartCodexDeviceLoginUseCaseImpl(gateway)
