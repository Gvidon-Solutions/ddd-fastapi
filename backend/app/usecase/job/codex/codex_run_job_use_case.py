"""Codex run job application use case."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from app.domain.file import FileKind, FileStatus
from app.domain.job import (
    Job,
    JobFile,
    JobFileRole,
    JobRepository,
)
from app.domain.job.codex_run_job_use_case import (
    CodexRunJobV1,
    CodexRunOutput,
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
    async def execute(self, job: CodexRunJobV1) -> CodexRunOutput:
        """Execute Codex for one persisted job."""


class CodexRunJobUseCaseImpl(CodexRunJobUseCase):
    """Execute Codex and persist its artifacts and events."""

    def __init__(
        self,
        jobs: JobRepository,
        storage: FileStorage,
        codex_executor: CodexExecutor,
        default_working_directory: Path,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.storage = storage
        self.codex_executor = codex_executor
        self.default_working_directory = default_working_directory

    async def execute(self, job: CodexRunJobV1) -> CodexRunOutput:
        """Execute Codex for one persisted job."""
        prompt = job.input.prompt
        job_workspace = self._job_workspace(job)

        now = _now()
        await self.jobs.append_event(
            job.id,
            Event1CodexRunStarted(
                created_at=now,
                payload=Event1CodexRunStartedPayload(
                    job_id=job.id,
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

            output_file_id = str(output_job_file.file_id) if output_job_file else None
            output = CodexRunOutput(
                output_file_id=output_file_id,
                log_files=exec_result.diagnostic_file_count(),
                generated_files=len(generated_files),
            )
            now = _now()
            await self.jobs.append_event(
                job.id,
                Event3CodexRunSucceeded(
                    created_at=now,
                    payload=Event3CodexRunSucceededPayload(
                        job_id=job.id,
                        output_file_id=output_file_id,
                        log_files=exec_result.diagnostic_file_count(),
                        generated_files=len(generated_files),
                    ),
                ),
            )
            return output
        except asyncio.CancelledError:
            await self.codex_executor.cancel()
            now = _now()
            reason = "Job cancelled"
            await self.jobs.append_event(
                job.id,
                Event5CodexRunCancelled(
                    created_at=now,
                    payload=Event5CodexRunCancelledPayload(
                        job_id=job.id,
                        reason=reason,
                    ),
                ),
            )
            raise
        except Exception as exc:
            now = _now()
            await self.jobs.append_event(
                job.id,
                Event4CodexRunFailed(
                    created_at=now,
                    payload=Event4CodexRunFailedPayload(
                        job_id=job.id,
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
        job_file = JobFile(
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
            job_id=job.id,
            role=role,
            description=description,
            attached_at=_now(),
        )
        await self.jobs.add_file(job_file)
        await self.jobs.append_event(
            job.id,
            Event2CodexRunFileCreated(
                created_at=_now(),
                payload=Event2CodexRunFileCreatedPayload(
                    job_id=job.id,
                    file_id=str(job_file.file_id),
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

    def _job_workspace(self, job: CodexRunJobV1) -> Path:
        """Return the workspace for a Codex run job."""
        workdir = job.input.workdir
        workspace_root = self.default_working_directory
        if workdir:
            workspace_root = Path(workdir)
        return workspace_root / str(job.id)


def new_codex_run_job_use_case(
    jobs: JobRepository,
    storage: FileStorage,
    codex_executor: CodexExecutor,
    default_working_directory: Path,
) -> CodexRunJobUseCase:
    """Instantiate the Codex run job use case."""
    return CodexRunJobUseCaseImpl(
        jobs=jobs,
        storage=storage,
        codex_executor=codex_executor,
        default_working_directory=default_working_directory,
    )

def _iter_files(root: Path) -> Iterable[Path]:
    """Yield regular files under a root directory."""
    return (path for path in root.rglob("*") if path.is_file())


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
