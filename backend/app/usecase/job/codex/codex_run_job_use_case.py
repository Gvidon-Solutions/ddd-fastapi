"""Codex run job application use case."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.job import (
    File,
    FileKind,
    FileStatus,
    Job,
    JobError,
    JobEventRepository,
    JobFile,
    JobFileRepository,
    JobFileRole,
    JobRepository,
    JobStatus,
)
from app.domain.job.codex_run_job_use_case import (
    CodexRunInputV1,
    CodexRunResultV1,
    Event1CodexRunStarted,
    Event1CodexRunStartedPayload,
    Event2CodexRunFileCreated,
    Event2CodexRunFileCreatedPayload,
    Event3CodexRunSucceeded,
    Event3CodexRunSucceededPayload,
    Event4CodexRunFailed,
    Event4CodexRunFailedPayload,
    Event5CodexRunCancelled,
    Event5CodexRunCancelledPayload,
)
from app.usecase.job.codex.ports import CodexExecResult, CodexExecutor
from app.usecase.job.ports import FileStorage


class CodexRunJobUseCase(ABC):
    """Define the application boundary for Codex run jobs."""

    @abstractmethod
    async def execute(self, job_id: UUID) -> dict:
        """Execute Codex for one persisted job."""


class CodexRunJobUseCaseImpl(CodexRunJobUseCase):
    """Execute Codex and persist its artifacts and events."""

    def __init__(
        self,
        jobs: JobRepository,
        job_files: JobFileRepository,
        storage: FileStorage,
        job_events: JobEventRepository,
        codex_executor: CodexExecutor,
        default_working_directory: Path,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.job_files = job_files
        self.storage = storage
        self.job_events = job_events
        self.codex_executor = codex_executor
        self.default_working_directory = default_working_directory

    async def execute(self, job_id: UUID) -> dict:
        """Execute Codex for one persisted job."""
        job = await self.jobs.get(job_id)
        prompt = _job_prompt(job)
        job_workspace = self._job_workspace(job)

        now = _now()
        await self.job_events.append(
            job.id,
            Event1CodexRunStarted(
                created_at=now,
                payload=Event1CodexRunStartedPayload(
                    stage="codex_run",
                    workdir=str(job_workspace),
                ),
            ),
        )

        try:
            exec_result = await self.codex_executor.codex_exec(
                prompt=prompt,
                workdir=job_workspace,
            )
            generated_files = await self._collect_generated_files(
                job=job,
                job_workspace=job_workspace,
            )
            await self._store_diagnostic_files(job, exec_result)
            exec_result.raise_for_failure()

            output_job_file = await self._store_codex_output(job, exec_result)

            output_file_id = (
                str(output_job_file.file.file_id) if output_job_file else None
            )
            result_payload = exec_result.summary(
                output_file_id=output_file_id,
                generated_files=len(generated_files),
            )
            now = _now()
            job.status = JobStatus.SUCCEEDED
            job.result = CodexRunResultV1(
                log_files=exec_result.diagnostic_file_count(),
                generated_files=len(generated_files),
            )
            job.finished_at = now
            job.updated_at = now
            job.error = None
            if await _mark_succeeded(self.jobs, job, job.result, now):
                await self.job_events.append(
                    job.id,
                    Event3CodexRunSucceeded(
                        created_at=now,
                        payload=Event3CodexRunSucceededPayload(
                            output_file_id=output_file_id,
                            log_files=exec_result.diagnostic_file_count(),
                            generated_files=len(generated_files),
                        ),
                    ),
                )
            return result_payload
        except asyncio.CancelledError:
            await self.codex_executor.cancel()
            now = _now()
            reason = "Job cancelled"
            job.error = JobError(
                code="CancelledError",
                message=reason,
            )
            job.finished_at = now
            job.updated_at = now
            job.status = JobStatus.CANCELLED
            if await _mark_cancelled(self.jobs, job, job.error, now):
                await self.job_events.append(
                    job.id,
                    Event5CodexRunCancelled(
                        created_at=now,
                        payload=Event5CodexRunCancelledPayload(
                            reason=reason,
                        ),
                    ),
                )
            raise
        except Exception as exc:
            now = _now()
            job.error = JobError(
                code=type(exc).__name__,
                message=str(exc),
            )
            job.finished_at = now
            job.updated_at = now
            job.status = JobStatus.FAILED
            if await _mark_failed(self.jobs, job, job.error, now):
                await self.job_events.append(
                    job.id,
                    Event4CodexRunFailed(
                        created_at=now,
                        payload=Event4CodexRunFailedPayload(
                            error=str(exc),
                        ),
                    ),
                )
            raise

    async def _store_diagnostic_files(
        self,
        job: Job,
        exec_result: CodexExecResult,
    ) -> None:
        """Persist diagnostic files captured while Codex ran."""
        for file in exec_result.diagnostic_files():
            await self._store_file(
                job=job,
                content=file.content,
                name=file.filename,
                role=JobFileRole.LOG,
                kind=FileKind.TEXT,
                metadata=file.metadata,
            )

    async def _store_codex_output(
        self,
        job: Job,
        exec_result: CodexExecResult,
    ) -> JobFile | None:
        """Persist the final Codex output file when it exists."""
        if not exec_result.output_text:
            return None
        return await self._store_file(
            job=job,
            content=exec_result.output_text.encode(),
            name="codex_result.txt",
            role=JobFileRole.PRIMARY_OUTPUT,
            kind=FileKind.TEXT,
            metadata={"filename": "codex_result.txt", "source": "codex"},
        )

    async def _store_file(
        self,
        *,
        job: Job,
        content: bytes | Path,
        name: str,
        role: JobFileRole,
        kind: FileKind,
        metadata: dict,
        description: str | None = None,
    ) -> JobFile:
        location = await self.storage.write(
            content=content,
            metadata=metadata,
        )
        file = File(
            file_id=uuid4(),
            name=name,
            kind=kind,
            location=location,
            metadata=metadata,
            status=FileStatus.ACTIVE,
            delete_requested_at=None,
            delete_attempts=0,
            last_delete_error=None,
            created_at=_now(),
        )
        job_file = JobFile(
            job_id=job.id,
            file=file,
            role=role,
            description=description,
            created_at=_now(),
        )
        await self.job_files.create(job_file)
        await self.job_events.append(
            job.id,
            Event2CodexRunFileCreated(
                created_at=_now(),
                payload=Event2CodexRunFileCreatedPayload(
                    file_id=str(file.file_id),
                    filename=name,
                ),
            ),
        )
        return job_file

    async def _collect_generated_files(
        self,
        *,
        job: Job,
        job_workspace: Path,
    ) -> list[JobFile]:
        """Persist all files generated in this Codex run directory."""
        generated_files: list[JobFile] = []
        for path in list(_iter_files(job_workspace)):
            relative_path = path.relative_to(job_workspace)
            job_file = await self._store_file(
                job=job,
                content=path,
                name=str(relative_path),
                role=JobFileRole.OUTPUT,
                kind=FileKind.FILE,
                metadata={
                    "filename": path.name,
                    "relative_path": str(relative_path),
                    "source": "codex",
                },
                description="Codex workspace file",
            )
            generated_files.append(job_file)
        return generated_files

    def _job_workspace(self, job: Job) -> Path:
        """Return the workspace for a Codex run job."""
        job_input = _codex_run_input(job)
        workdir = job_input.workdir
        workspace_root = self.default_working_directory
        if workdir:
            workspace_root = Path(workdir)
        return workspace_root / str(job.id)


def new_codex_run_job_use_case(
    jobs: JobRepository,
    job_files: JobFileRepository,
    storage: FileStorage,
    job_events: JobEventRepository,
    codex_executor: CodexExecutor,
    default_working_directory: Path,
) -> CodexRunJobUseCase:
    """Instantiate the Codex run job use case."""
    return CodexRunJobUseCaseImpl(
        jobs=jobs,
        job_files=job_files,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=default_working_directory,
    )


def _job_prompt(job: Job) -> str:
    """Return the prompt for a Codex run job."""
    prompt = _codex_run_input(job).prompt
    if not prompt.strip():
        raise ValueError("codex_run job requires input.prompt")
    return prompt


def _codex_run_input(job: Job) -> CodexRunInputV1:
    if isinstance(job.input, CodexRunInputV1):
        return job.input
    if isinstance(job.input, dict):
        return CodexRunInputV1(**job.input)
    raise ValueError("codex_run job requires CodexRunInputV1")


def _iter_files(root: Path) -> Iterable[Path]:
    """Yield regular files under a root directory."""
    return (path for path in root.rglob("*") if path.is_file())


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)


async def _mark_succeeded(
    jobs: JobRepository,
    job: Job,
    result: object,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_succeeded(
            job.id,
            result=result,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True


async def _mark_failed(
    jobs: JobRepository,
    job: Job,
    error: JobError,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_failed(
            job.id,
            error=error,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True


async def _mark_cancelled(
    jobs: JobRepository,
    job: Job,
    error: JobError,
    finished_at: datetime,
) -> bool:
    try:
        return await jobs.try_mark_cancelled(
            job.id,
            error=error,
            finished_at=finished_at,
        )
    except NotImplementedError:
        await jobs.save(job)
        return True
