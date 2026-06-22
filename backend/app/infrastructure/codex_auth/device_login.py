"""Run Codex CLI device-auth login sessions."""

from __future__ import annotations

import asyncio
import re
import uuid
from uuid import UUID

from app.config import settings
from app.domain.codex_auth.entities import CodexDeviceLoginSession, CodexLoginStatus
from app.domain.codex_auth.value_objects import CodexDeviceLoginStatus
from app.usecase.codex_auth.ports import CodexDeviceLoginGateway

_URL_PATTERN = re.compile(r"https://[^\s]+")
_CODE_PATTERNS = (
    re.compile(r"\b([A-Z0-9]{4,}(?:-[A-Z0-9]{4,})+)\b"),
    re.compile(r"(?:code|user code|device code)[:\s]+([A-Z0-9-]{6,})", re.IGNORECASE),
)


class _CodexDeviceLoginProcessSession:
    """Track one running Codex device login process."""

    def __init__(
        self,
        id: uuid.UUID,
        process: asyncio.subprocess.Process,
    ):
        """Store process-backed login session state."""
        self.id = id
        self.process = process
        self.output: list[str] = []
        self.verification_url: str | None = None
        self.user_code: str | None = None
        self.completed = False
        self.return_code: int | None = None

    @property
    def status(self) -> CodexDeviceLoginStatus:
        """Return the status for this login session."""
        if self.completed and self.return_code == 0:
            return CodexDeviceLoginStatus.COMPLETED
        if self.completed:
            return CodexDeviceLoginStatus.FAILED
        return CodexDeviceLoginStatus.PENDING

    @property
    def raw_output(self) -> str:
        """Return collected CLI output."""
        return "".join(self.output)

    def update_from_output(self, chunk: str) -> None:
        """Store output and extract device-login metadata."""
        self.output.append(chunk)
        parsed = parse_device_login_output(self.raw_output)
        self.verification_url = parsed["verification_url"]
        self.user_code = parsed["user_code"]


def parse_device_login_output(output: str) -> dict[str, str | None]:
    """Extract the verification URL and user code from Codex CLI output."""
    url_match = _URL_PATTERN.search(output)
    user_code = None
    for pattern in _CODE_PATTERNS:
        code_match = pattern.search(output)
        if code_match:
            user_code = code_match.group(1)
            break

    return {
        "verification_url": url_match.group(0) if url_match else None,
        "user_code": user_code,
    }


class CodexDeviceLoginManager(CodexDeviceLoginGateway):
    """Manage Codex device login subprocesses."""

    def __init__(self) -> None:
        """Initialize in-memory session storage."""
        self._sessions: dict[uuid.UUID, _CodexDeviceLoginProcessSession] = {}
        self._reader_tasks: dict[uuid.UUID, asyncio.Task[None]] = {}

    async def start(self) -> CodexDeviceLoginSession:
        """Start a Codex device-auth login process."""
        process = await asyncio.create_subprocess_exec(
            settings.CODEX_CLI_PATH,
            "login",
            "--device-auth",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        session = _CodexDeviceLoginProcessSession(id=uuid.uuid4(), process=process)
        self._sessions[session.id] = session
        self._reader_tasks[session.id] = asyncio.create_task(self._read_output(session))
        await self._wait_until_ready(session)
        return self._to_entity(session)

    async def find_by_id(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Return a tracked login session."""
        session = self._get_process_session(session_id)
        return self._to_entity(session) if session else None

    async def cancel(self, session_id: UUID) -> CodexDeviceLoginSession | None:
        """Terminate a running login session."""
        session = self._get_process_session(session_id)
        if session is None:
            return None
        if not session.completed:
            session.process.terminate()
            await session.process.wait()
            session.completed = True
            session.return_code = session.process.returncode
        return self._to_entity(session)

    async def status(self) -> CodexLoginStatus:
        """Return whether Codex CLI is already authenticated."""
        process = await asyncio.create_subprocess_exec(
            settings.CODEX_CLI_PATH,
            "login",
            "status",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await process.communicate()
        return CodexLoginStatus(
            authenticated=process.returncode == 0,
            raw_output=stdout.decode(errors="replace"),
        )

    def _get_process_session(
        self,
        session_id: UUID,
    ) -> _CodexDeviceLoginProcessSession | None:
        """Return and refresh a process-backed session."""
        session = self._sessions.get(session_id)
        if session and not session.completed and session.process.returncode is not None:
            session.completed = True
            session.return_code = session.process.returncode
        return session

    def _to_entity(
        self,
        session: _CodexDeviceLoginProcessSession,
    ) -> CodexDeviceLoginSession:
        """Convert a process-backed session to a domain entity."""
        return CodexDeviceLoginSession(
            id=session.id,
            status=session.status,
            verification_url=session.verification_url,
            user_code=session.user_code,
            raw_output=session.raw_output,
            return_code=session.return_code,
        )

    async def _read_output(self, session: _CodexDeviceLoginProcessSession) -> None:
        """Read Codex CLI output until the process exits."""
        assert session.process.stdout is not None
        while line := await session.process.stdout.readline():
            session.update_from_output(line.decode(errors="replace"))
        await session.process.wait()
        session.completed = True
        session.return_code = session.process.returncode

    async def _wait_until_ready(self, session: _CodexDeviceLoginProcessSession) -> None:
        """Wait briefly until the CLI prints URL/code or exits."""
        deadline = asyncio.get_running_loop().time() + (
            settings.CODEX_DEVICE_LOGIN_START_TIMEOUT_SECONDS
        )
        while asyncio.get_running_loop().time() < deadline:
            if session.verification_url or session.user_code or session.completed:
                return
            await asyncio.sleep(0.1)


codex_device_login_manager = CodexDeviceLoginManager()
