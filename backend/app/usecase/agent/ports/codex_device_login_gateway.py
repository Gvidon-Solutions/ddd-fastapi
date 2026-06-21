"""Codex device login gateway port."""

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.agent.entities import CodexDeviceLoginSession, CodexLoginStatus


class CodexDeviceLoginGateway(ABC):
    """Provide Codex CLI device authentication operations."""

    @abstractmethod
    async def status(self) -> CodexLoginStatus:
        """Return whether Codex CLI is authenticated."""

    @abstractmethod
    async def start(self) -> CodexDeviceLoginSession:
        """Start Codex CLI device-code authentication."""

    @abstractmethod
    async def find_by_id(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Return a device login session by ID."""

    @abstractmethod
    async def cancel(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Cancel a device login session."""
