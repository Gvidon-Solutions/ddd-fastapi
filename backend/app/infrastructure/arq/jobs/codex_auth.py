"""Codex auth ARQ task."""

from __future__ import annotations

import asyncio
import os
import re
from pathlib import Path
from typing import Annotated, Any
from uuid import UUID, uuid4

from fast_depends import Depends, inject

from app.config import settings
from app.domain.job import (
    JobError,
    JobEvent,
    JobEventRepository,
    JobEventType,
    JobRepository,
    JobStage,
    JobStatus,
)
from app.infrastructure.arq.deps import (
    JobTaskTransaction,
    get_clock,
    get_job_event_repository,
    get_job_repository,
    get_job_task_transaction,
)
from app.usecase.job import Clock

_URL_PATTERN = re.compile(r"https://[^\s]+")
_CODE_PATTERNS = (
    re.compile(r"\b([A-Z0-9]{4,}(?:-[A-Z0-9]{4,})+)\b"),
    re.compile(r"(?:code|user code|device code)[:\s]+([A-Z0-9-]{6,})", re.IGNORECASE),
)


@inject
async def codex_auth(
    ctx: dict[str, Any],
    job_id: str,
    jobs: Annotated[JobRepository, Depends(get_job_repository)],
    job_events: Annotated[JobEventRepository, Depends(get_job_event_repository)],
    clock: Annotated[Clock, Depends(get_clock)],
    transaction: Annotated[JobTaskTransaction, Depends(get_job_task_transaction)],
) -> dict:
    """Run Codex device auth and persist login metadata in job stage."""
    del ctx
    return await execute_codex_auth(
        job_id=UUID(job_id),
        jobs=jobs,
        job_events=job_events,
        clock=clock,
        transaction=transaction,
    )


async def execute_codex_auth(
    job_id: UUID,
    jobs: JobRepository,
    job_events: JobEventRepository,
    clock: Clock,
    transaction: JobTaskTransaction | None = None,
    process_factory: Any = asyncio.create_subprocess_exec,
) -> dict:
    """Execute Codex device auth for one persisted job."""
    job = await jobs.get(job_id)

    job.status = JobStatus.RUNNING
    job.stage = JobStage(
        key="codex_auth",
        message="Starting Codex device auth",
        data={"status": "starting"},
    )
    job.started_at = clock.now()
    await jobs.save(job)
    await job_events.append(
        JobEvent(
            id=uuid4(),
            job_id=job.id,
            type=JobEventType.STARTED,
            data={"stage": "codex_auth"},
            message="Starting Codex device auth",
            created_at=clock.now(),
        )
    )
    await _commit(transaction)

    try:
        process = await process_factory(
            settings.CODEX_CLI_PATH,
            "login",
            "--device-auth",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=_codex_env(),
        )
        assert process.stdout is not None

        raw_output_parts: list[str] = []
        stage_data: dict[str, Any] = {
            "status": "pending",
            "verification_url": None,
            "user_code": None,
            "raw_output": "",
            "return_code": None,
        }

        while line := await process.stdout.readline():
            raw_output_parts.append(line.decode(errors="replace"))
            parsed = parse_device_login_output("".join(raw_output_parts))
            stage_data = {
                "status": "pending",
                "verification_url": parsed["verification_url"],
                "user_code": parsed["user_code"],
                "raw_output": "".join(raw_output_parts),
                "return_code": None,
            }
            job.stage = JobStage(
                key="codex_auth",
                message="Open verification URL and enter user code",
                data=stage_data,
            )
            await jobs.save(job)
            await job_events.append(
                JobEvent(
                    id=uuid4(),
                    job_id=job.id,
                    type=JobEventType.STAGE_CHANGED,
                    data={
                        "stage": "codex_auth",
                        "verification_url": parsed["verification_url"],
                        "user_code": parsed["user_code"],
                    },
                    message="Open verification URL and enter user code",
                    created_at=clock.now(),
                )
            )
            await _commit(transaction)

        return_code = await process.wait()
        stage_data = {
            **stage_data,
            "status": "authenticated" if return_code == 0 else "failed",
            "return_code": return_code,
        }
        job.stage = JobStage(
            key="codex_auth",
            message="Codex auth completed" if return_code == 0 else "Codex auth failed",
            data=stage_data,
        )
        await jobs.save(job)
        await job_events.append(
            JobEvent(
                id=uuid4(),
                job_id=job.id,
                type=JobEventType.STAGE_CHANGED,
                data={"stage": "codex_auth", "status": stage_data["status"]},
                message=job.stage.message,
                created_at=clock.now(),
            )
        )
        await _commit(transaction)

        if return_code != 0:
            raise RuntimeError(f"Codex auth exited with code {return_code}")

        result_summary = {
            "authenticated": True,
            "verification_url": stage_data["verification_url"],
            "user_code": stage_data["user_code"],
        }
        job.status = JobStatus.SUCCEEDED
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
                message="Codex auth completed",
                created_at=clock.now(),
            )
        )
        await _commit(transaction)
        return result_summary
    except Exception as exc:
        job.status = JobStatus.FAILED
        job.error = JobError(
            code=type(exc).__name__,
            message=str(exc),
        )
        job.stage = JobStage(
            key="codex_auth",
            message="Codex auth failed",
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
        await _commit(transaction)
        raise


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


def _codex_env() -> dict[str, str]:
    """Return environment variables for Codex auth subprocesses."""
    codex_home = Path(settings.CODEX_JOB_WORKING_DIRECTORY)
    codex_home.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HOME"] = str(codex_home)
    return env


async def _commit(transaction: JobTaskTransaction | None) -> None:
    """Commit context changes when a database session is present."""
    if transaction is not None:
        await transaction.commit()
