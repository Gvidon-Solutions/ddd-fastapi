"""Define the Codex authenticator port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job.codex_auth_job_use_case import CodexAuthResult, CodexDeviceAuth


class CodexAuthenticator(ABC):
    """Authenticate the Codex CLI."""

    @abstractmethod
    async def start_device_auth(self) -> CodexDeviceAuth:
        """Start Codex device auth and return login data."""

    @abstractmethod
    async def await_for_user_login(self) -> CodexAuthResult:
        """Wait until the user completes Codex device auth."""
