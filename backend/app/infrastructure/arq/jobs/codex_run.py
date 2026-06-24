"""Codex run ARQ task."""

from __future__ import annotations

import asyncio
import json
import os
from collections.abc import Sequence
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.job import (
    ArtifactKind,
    ArtifactRole,
    Job,
    JobArtifact,
    JobArtifactRepository,
    JobError,
    JobEvent,
    JobEventRepository,
    JobEventType,
    JobRepository,
    JobStage,
    JobStatus,
)
from app.infrastructure.arq.deps import (
    ARQ_ARTIFACT_STORAGE,
    ARQ_CLOCK,
    get_arq_db_engine,
    new_arq_job_artifact_repository,
    new_arq_job_event_repository,
    new_arq_job_repository,
)
from app.usecase.job import ArtifactStorage, Clock


async def codex_run(
    ctx: dict[str, Any],
    job_id: str,
) -> dict:
    """Run Codex exec for one persisted job."""
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            return await execute_codex_run(
                job_id=UUID(job_id),
                jobs=new_arq_job_repository(session),
                artifacts=new_arq_job_artifact_repository(session),
                storage=ctx[ARQ_ARTIFACT_STORAGE],
                job_events=new_arq_job_event_repository(session),
                clock=ctx[ARQ_CLOCK],
            )
        except Exception:
            await session.rollback()
            raise


async def execute_codex_run(
    job_id: UUID,
    jobs: JobRepository,
    artifacts: JobArtifactRepository,
    storage: ArtifactStorage,
    job_events: JobEventRepository,
    clock: Clock,
    process_factory: Any = asyncio.create_subprocess_exec,
) -> dict:
    """Execute Codex for one persisted job."""
    job = await jobs.get(job_id)
    prompt = _job_prompt(job)
    job_workspace = _job_workspace(job)
    output_path = job_workspace / ".codex-output.txt"

    job.status = JobStatus.RUNNING
    job.stage = JobStage(
        key="codex_run",
        message="Running Codex",
        data={"status": "running", "workdir": str(job_workspace)},
    )
    job.started_at = clock.now()
    await jobs.save(job)
    await job_events.append(
        JobEvent(
            id=uuid4(),
            job_id=job.id,
            type=JobEventType.STARTED,
            data={"stage": "codex_run", "workdir": str(job_workspace)},
            message="Running Codex",
            created_at=clock.now(),
        )
    )

    stdout_lines: list[str] = []
    stderr_lines: list[str] = []
    try:
        job_workspace.mkdir(parents=True, exist_ok=True)
        process = await process_factory(
            *_codex_exec_args(
                job_workspace=job_workspace,
                output_path=output_path,
            ),
            cwd=job_workspace,
            env=_codex_env(),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        assert process.stderr is not None

        stdout_task = asyncio.create_task(_read_lines(process.stdout, stdout_lines))
        stderr_task = asyncio.create_task(_read_lines(process.stderr, stderr_lines))
        process.stdin.write(prompt.encode())
        await process.stdin.drain()
        process.stdin.close()
        await process.stdin.wait_closed()
        return_code = await process.wait()
        await stdout_task
        await stderr_task

        result = _read_codex_result(output_path, stdout_lines)
        stdout_count = len(stdout_lines)
        stderr_count = len(stderr_lines)
        error_output = "\n".join(stderr_lines).strip()

        if stdout_lines:
            stdout_metadata = {"filename": "codex_stdout.jsonl", "source": "codex"}
            stdout_location = await storage.write(
                content=("\n".join(stdout_lines) + "\n").encode(),
                metadata=stdout_metadata,
            )
            stdout_artifact = JobArtifact(
                id=uuid4(),
                job_id=job.id,
                role=ArtifactRole.LOG,
                kind=ArtifactKind.TEXT,
                location=stdout_location,
                metadata=stdout_metadata,
                created_at=clock.now(),
            )
            await artifacts.create(stdout_artifact)
            await job_events.append(
                JobEvent(
                    id=uuid4(),
                    job_id=job.id,
                    type=JobEventType.ARTIFACT_CREATED,
                    data={
                        "artifact_id": str(stdout_artifact.id),
                        "filename": stdout_metadata["filename"],
                    },
                    message="Created artifact codex_stdout.jsonl",
                    created_at=clock.now(),
                )
            )

        if stderr_lines:
            stderr_metadata = {"filename": "codex_stderr.log", "source": "codex"}
            stderr_location = await storage.write(
                content=("\n".join(stderr_lines) + "\n").encode(),
                metadata=stderr_metadata,
            )
            stderr_artifact = JobArtifact(
                id=uuid4(),
                job_id=job.id,
                role=ArtifactRole.LOG,
                kind=ArtifactKind.TEXT,
                location=stderr_location,
                metadata=stderr_metadata,
                created_at=clock.now(),
            )
            await artifacts.create(stderr_artifact)
            await job_events.append(
                JobEvent(
                    id=uuid4(),
                    job_id=job.id,
                    type=JobEventType.ARTIFACT_CREATED,
                    data={
                        "artifact_id": str(stderr_artifact.id),
                        "filename": stderr_metadata["filename"],
                    },
                    message="Created artifact codex_stderr.log",
                    created_at=clock.now(),
                )
            )

        if return_code != 0:
            if not error_output:
                error_output = f"Codex CLI exited with code {return_code}"
            raise RuntimeError(error_output)

        output_artifact = None
        if result:
            output_metadata = {"filename": "codex_result.txt", "source": "codex"}
            output_location = await storage.write(
                content=result.encode(),
                metadata=output_metadata,
            )
            output_artifact = JobArtifact(
                id=uuid4(),
                job_id=job.id,
                role=ArtifactRole.OUTPUT,
                kind=ArtifactKind.TEXT,
                location=output_location,
                metadata=output_metadata,
                created_at=clock.now(),
            )
            await artifacts.create(output_artifact)
            await job_events.append(
                JobEvent(
                    id=uuid4(),
                    job_id=job.id,
                    type=JobEventType.ARTIFACT_CREATED,
                    data={
                        "artifact_id": str(output_artifact.id),
                        "filename": output_metadata["filename"],
                    },
                    message="Created artifact codex_result.txt",
                    created_at=clock.now(),
                )
            )

        result_summary = {
            "return_code": return_code,
            "output_artifact_id": str(output_artifact.id) if output_artifact else None,
            "stdout_lines": stdout_count,
            "stderr_lines": stderr_count,
        }
        job.status = JobStatus.SUCCEEDED
        job.stage = JobStage(
            key="codex_run",
            message="Codex finished",
            data={"status": "succeeded", **result_summary},
        )
        job.result_summary = result_summary
        job.finished_at = clock.now()
        job.error = None
        await jobs.save(job)
        await job_events.append(
            JobEvent(
                id=uuid4(),
                job_id=job.id,
                type=JobEventType.SUCCEEDED,
                data={"summary": result_summary},
                message="Codex finished",
                created_at=clock.now(),
            )
        )
        return result_summary
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = JobError(
            code=type(exc).__name__,
            message=str(exc),
        )
        job.stage = JobStage(
            key="codex_run",
            message="Codex failed",
            data={"status": "failed", "error": str(exc)},
        )
        job.finished_at = clock.now()
        await jobs.save(job)
        await job_events.append(
            JobEvent(
                id=uuid4(),
                job_id=job.id,
                type=JobEventType.FAILED,
                data={"error": str(exc)},
                message=str(exc),
                created_at=clock.now(),
            )
        )
        raise
    finally:
        output_path.unlink(missing_ok=True)


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


def _job_prompt(job: Job) -> str:
    """Return the prompt for a Codex run job."""
    job_input = job.input or {}
    prompt = job_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("codex_run job requires input.prompt")
    return prompt


def _job_workspace(job: Job) -> Path:
    """Return the workspace for a Codex run job."""
    job_input = job.input or {}
    workdir = job_input.get("workdir")
    if isinstance(workdir, str) and workdir:
        return Path(workdir)
    return Path(settings.CODEX_JOB_WORKING_DIRECTORY) / str(job.id)


def _codex_env() -> dict[str, str]:
    """Return environment variables for Codex subprocesses."""
    codex_home = Path(settings.CODEX_JOB_WORKING_DIRECTORY)
    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(codex_home)
    return env


async def _read_lines(
    stream: asyncio.StreamReader,
    lines: list[str],
) -> None:
    """Read stream lines into a list."""
    while line := await stream.readline():
        decoded_line = line.decode(errors="replace").strip()
        if decoded_line:
            lines.append(decoded_line)


def _read_codex_result(output_path: Path, stdout_lines: Sequence[str]) -> str:
    """Read Codex output file with a stdout fallback."""
    if output_path.is_file():
        return output_path.read_text(encoding="utf-8").strip()
    return _fallback_result(stdout_lines)


def _fallback_result(stdout_lines: Sequence[str]) -> str:
    """Return a best-effort result from streamed stdout events."""
    for line in reversed(stdout_lines):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            if line:
                return line
            continue
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
