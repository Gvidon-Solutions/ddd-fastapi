"""Codex job runner implementation."""

import asyncio
import json
import os
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from app.config import settings
from app.domain.codex_job.entities import CodexJob
from app.infrastructure.redis import new_codex_job_event_publisher
from app.usecase.codex_job import CodexJobEventPublisher, CodexJobRunner


def _event_type(event: Any) -> str:
    """Return a stable event type string."""
    if isinstance(event, dict):
        event_type = event.get("type")
        if isinstance(event_type, str) and event_type:
            return event_type

    event_type = getattr(event, "type", None)
    if isinstance(event_type, str) and event_type:
        return event_type
    return type(event).__name__


def _event_payload(event: Any) -> str:
    """Serialize one Codex stream event."""
    model_dump_json = getattr(event, "model_dump_json", None)
    if callable(model_dump_json):
        return str(model_dump_json())

    model_dump = getattr(event, "model_dump", None)
    if callable(model_dump):
        return json.dumps(model_dump(mode="json"), default=str)

    return json.dumps(event, default=_json_default)


def _json_default(value: Any) -> Any:
    """Serialize non-standard event payload values."""
    if is_dataclass(value):
        object_value = getattr(value, "value", None)
        if isinstance(object_value, str | int | float | bool | None):
            return object_value
        return asdict(value)
    return str(value)


def _codex_exec_args(
    *,
    job_workspace: Path,
    output_path: Path,
) -> list[str]:
    """Build the Codex CLI command for one non-interactive job."""
    return [
        settings.CODEX_CLI_PATH,
        "exec",
        "--json",
        "--strict-config",
        "--skip-git-repo-check",
        "-C",
        str(job_workspace),
        "-m",
        settings.CODEX_JOB_MODEL,
        "-s",
        settings.CODEX_JOB_SANDBOX_MODE,
        "-c",
        f'model_reasoning_effort="{settings.CODEX_JOB_REASONING_EFFORT}"',
        "-c",
        f'approval_policy="{settings.CODEX_JOB_APPROVAL_POLICY}"',
        "-o",
        str(output_path),
        "-",
    ]


class CodexCliJobRunner(CodexJobRunner):
    """Execute Codex jobs."""

    def __init__(self, event_publisher: CodexJobEventPublisher):
        """Store runner dependencies."""
        self.event_publisher = event_publisher

    async def execute(self, codex_job: CodexJob) -> str:
        """Run a Codex job and return its result."""
        codex_home = Path(settings.CODEX_JOB_WORKING_DIRECTORY)
        job_workspace = codex_home / str(codex_job.id.value)
        job_workspace.mkdir(parents=True, exist_ok=True)
        output_path = job_workspace / ".codex-output.txt"
        process = await asyncio.create_subprocess_exec(
            *_codex_exec_args(job_workspace=job_workspace, output_path=output_path),
            cwd=job_workspace,
            env=self._process_env(codex_home),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None

        stderr_lines: list[str] = []
        stdout_task = asyncio.create_task(self._publish_stdout(codex_job, process.stdout))
        stderr_task = asyncio.create_task(
            self._publish_stderr(codex_job, process.stderr, stderr_lines)
        )
        process.stdin.write(codex_job.prompt.value.encode())
        await process.stdin.drain()
        process.stdin.close()
        await process.stdin.wait_closed()
        return_code = await process.wait()
        stdout_events = await stdout_task
        await stderr_task

        try:
            result = output_path.read_text(encoding="utf-8").strip()
        finally:
            output_path.unlink(missing_ok=True)

        if return_code != 0:
            error_output = "\n".join(stderr_lines).strip()
            if not error_output:
                error_output = f"Codex CLI exited with code {return_code}"
            raise RuntimeError(error_output)

        if result:
            return result

        return self._fallback_result(stdout_events)

    def _process_env(self, codex_home: Path) -> dict[str, str]:
        """Return environment variables for the Codex CLI process."""
        env = os.environ.copy()
        env["HOME"] = str(codex_home)
        return env

    async def _publish_stdout(
        self,
        codex_job: CodexJob,
        stdout: asyncio.StreamReader,
    ) -> list[Any]:
        """Publish Codex JSONL stdout events."""
        events: list[Any] = []
        while line := await stdout.readline():
            decoded_line = line.decode(errors="replace").strip()
            if not decoded_line:
                continue
            try:
                event: Any = json.loads(decoded_line)
            except json.JSONDecodeError:
                event = {"type": "codex_stdout", "message": decoded_line}
            events.append(event)
            await self.event_publisher.publish(
                codex_job_id=codex_job.id,
                event_type=_event_type(event),
                payload=_event_payload(event),
            )
        return events

    async def _publish_stderr(
        self,
        codex_job: CodexJob,
        stderr: asyncio.StreamReader,
        stderr_lines: list[str],
    ) -> None:
        """Publish Codex stderr output."""
        while line := await stderr.readline():
            decoded_line = line.decode(errors="replace").strip()
            if not decoded_line:
                continue
            stderr_lines.append(decoded_line)
            await self.event_publisher.publish(
                codex_job_id=codex_job.id,
                event_type="codex_stderr",
                payload=_event_payload(
                    {
                        "type": "codex_stderr",
                        "message": decoded_line,
                    }
                ),
            )

    def _fallback_result(self, events: Sequence[Any]) -> str:
        """Return a best-effort final result from streamed events."""
        for event in reversed(events):
            if not isinstance(event, dict):
                continue
            for key in ("message", "text", "content"):
                value = event.get(key)
                if isinstance(value, str) and value:
                    return value
            item = event.get("item")
            if isinstance(item, dict):
                for key in ("message", "text", "content"):
                    value = item.get(key)
                    if isinstance(value, str) and value:
                        return value
        return ""


def new_codex_job_runner(
    event_publisher: CodexJobEventPublisher | None = None,
) -> CodexJobRunner:
    """Create a Codex job runner."""
    return CodexCliJobRunner(event_publisher or new_codex_job_event_publisher())
