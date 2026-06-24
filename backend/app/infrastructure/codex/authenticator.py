"""Codex CLI authenticator implementation."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path

from app.config import settings
from app.domain.job.codex_auth_job_use_case import CodexAuthResult, CodexDeviceAuth
from app.usecase.job.codex import CodexAuthenticator

_URL_PATTERN = re.compile(r"https://[^\s]+")
_ANSI_PATTERN = re.compile(r"\x1b\[[0-9;]*m")
_CODE_PATTERNS = (
    re.compile(r"\b([A-Z0-9]{4,}(?:-[A-Z0-9]{4,})+)\b"),
    re.compile(r"(?:code|user code|device code)[:\s]+([A-Z0-9-]{6,})", re.IGNORECASE),
)


class CodexCliAuthenticator(CodexAuthenticator):
    """Authenticate Codex through the Codex CLI."""

    def __init__(self) -> None:
        """Initialize process state."""
        self.process: asyncio.subprocess.Process | None = None
        self.raw_output_parts: list[str] = []
        self.device_auth: CodexDeviceAuth | None = None

    async def start_device_auth(self) -> CodexDeviceAuth:
        """Start Codex CLI device auth and return login data."""
        if self.process is not None and self.process.returncode is None:
            raise RuntimeError("Codex device auth is already running")

        self.raw_output_parts = []
        self.device_auth = None
        self.process = await asyncio.create_subprocess_exec(
            settings.CODEX_CLI_PATH,
            "login",
            "--device-auth",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=_codex_env(),
        )
        assert self.process.stdout is not None

        while line := await self.process.stdout.readline():
            self.raw_output_parts.append(line.decode(errors="replace"))
            raw_output = "".join(self.raw_output_parts)
            parsed = parse_device_login_output(raw_output)
            self.device_auth = CodexDeviceAuth(
                verification_url=parsed["verification_url"],
                device_code=parsed["device_code"],
            )
            if self.device_auth.verification_url and self.device_auth.device_code:
                return self.device_auth

        return_code = await self.process.wait()
        self.process = None
        raise RuntimeError(f"Codex auth did not produce device login: {return_code}")

    async def await_for_user_login(self) -> CodexAuthResult:
        """Wait until the Codex CLI device auth process exits."""
        if self.process is None:
            raise RuntimeError("Codex device auth is not running")

        if self.process.stdout is not None:
            while line := await self.process.stdout.readline():
                self.raw_output_parts.append(line.decode(errors="replace"))

        return_code = await self.process.wait()
        self.process = None
        if return_code != 0:
            return CodexAuthResult(
                authenticated=False,
                error_message=f"Codex auth exited with code {return_code}",
            )
        return CodexAuthResult(authenticated=True)

    async def cancel(self) -> bool:
        """Cancel the currently running Codex auth process."""
        process = self.process
        if process is None or process.returncode is not None:
            return False

        process.terminate()
        try:
            await asyncio.wait_for(process.wait(), timeout=5)
        except TimeoutError:
            process.kill()
            await process.wait()
        self.process = None
        return True


def parse_device_login_output(output: str) -> dict[str, str | None]:
    """Extract the verification URL and device code from Codex CLI output."""
    output = _ANSI_PATTERN.sub("", output)
    url_match = _URL_PATTERN.search(output)
    device_code = None
    for pattern in _CODE_PATTERNS:
        code_match = pattern.search(output)
        if code_match and _is_device_code_candidate(code_match.group(1)):
            device_code = code_match.group(1)
            break

    return {
        "verification_url": url_match.group(0) if url_match else None,
        "device_code": device_code,
    }


def _is_device_code_candidate(value: str) -> bool:
    return any(character.isdigit() for character in value) or "-" in value


def _codex_env() -> dict[str, str]:
    """Return environment variables for Codex auth subprocesses."""
    codex_home = Path(settings.CODEX_JOB_WORKING_DIRECTORY)
    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(codex_home)
    return env


def new_codex_authenticator() -> CodexAuthenticator:
    """Create a Codex CLI authenticator."""
    return CodexCliAuthenticator()
