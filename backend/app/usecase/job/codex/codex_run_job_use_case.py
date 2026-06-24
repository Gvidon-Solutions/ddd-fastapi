"""Codex run job application use case."""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from app.domain.job import (
    ArtifactKind,
    ArtifactRole,
    Job,
    JobArtifact,
    JobArtifactRepository,
    JobError,
    JobEventRepository,
    JobRepository,
    JobStatus,
)
from app.domain.job.codex_run_job_use_case import (
    Event1CodexRunStarted,
    Event1CodexRunStartedPayload,
    Event2CodexRunArtifactCreated,
    Event2CodexRunArtifactCreatedPayload,
    Event3CodexRunSucceeded,
    Event3CodexRunSucceededPayload,
    Event4CodexRunFailed,
    Event4CodexRunFailedPayload,
    Event5CodexRunCancelled,
    Event5CodexRunCancelledPayload,
    Stage1RunningCodex,
    Stage1RunningCodexData,
    Stage2CodexRunCompleted,
    Stage2CodexRunCompletedData,
    Stage3CodexRunFailed,
    Stage3CodexRunFailedData,
    Stage4CodexRunCancelled,
    Stage4CodexRunCancelledData,
)
from app.usecase.job.codex.ports import CodexExecResult, CodexExecutor
from app.usecase.job.ports import ArtifactStorage


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
        artifacts: JobArtifactRepository,
        storage: ArtifactStorage,
        job_events: JobEventRepository,
        codex_executor: CodexExecutor,
        default_working_directory: Path,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.artifacts = artifacts
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
        job.job_status = JobStatus.RUNNING
        job.job_stage = Stage1RunningCodex(
            updated_at=now,
            data=Stage1RunningCodexData(workdir=str(job_workspace)),
        )
        job.started_at = now
        job.updated_at = now
        await self.jobs.save(job)
        await self.job_events.append(
            Event1CodexRunStarted(
                created_at=now,
                payload=Event1CodexRunStartedPayload(
                    job_id_issuer=job.job_id,
                    stage="codex_run",
                    workdir=str(job_workspace),
                ),
            )
        )

        try:
            exec_result = await self.codex_executor.codex_exec(
                prompt=prompt,
                workdir=job_workspace,
            )
            generated_artifacts = await self._collect_generated_artifacts(
                job=job,
                job_workspace=job_workspace,
            )
            await self._store_diagnostic_artifacts(job, exec_result)
            exec_result.raise_for_failure()

            output_artifact = await self._store_codex_output(job, exec_result)

            output_artifact_id = (
                str(output_artifact.artifact_id) if output_artifact else None
            )
            result_summary = exec_result.summary(
                output_artifact_id=output_artifact_id,
                generated_artifacts=len(generated_artifacts),
            )
            now = _now()
            job.job_status = JobStatus.SUCCEEDED
            job.job_stage = Stage2CodexRunCompleted(
                updated_at=now,
                data=Stage2CodexRunCompletedData(
                    output_artifact_id=output_artifact_id,
                    log_artifacts=exec_result.diagnostic_artifact_count(),
                    generated_artifacts=len(generated_artifacts),
                ),
            )
            job.result_summary = result_summary
            job.finished_at = now
            job.updated_at = now
            job.job_error = None
            await self.jobs.save(job)
            await self.job_events.append(
                Event3CodexRunSucceeded(
                    created_at=now,
                    payload=Event3CodexRunSucceededPayload(
                        job_id_issuer=job.job_id,
                        output_artifact_id=output_artifact_id,
                        log_artifacts=exec_result.diagnostic_artifact_count(),
                        generated_artifacts=len(generated_artifacts),
                    ),
                )
            )
            return result_summary
        except asyncio.CancelledError:
            await self.codex_executor.cancel()
            now = _now()
            reason = "Job cancelled"
            job.job_status = JobStatus.CANCELLED
            job.job_error = JobError(
                code="CancelledError",
                message=reason,
            )
            job.job_stage = Stage4CodexRunCancelled(
                updated_at=now,
                data=Stage4CodexRunCancelledData(reason=reason),
            )
            job.finished_at = now
            job.updated_at = now
            await self.jobs.save(job)
            await self.job_events.append(
                Event5CodexRunCancelled(
                    created_at=now,
                    payload=Event5CodexRunCancelledPayload(
                        job_id_issuer=job.job_id,
                        reason=reason,
                    ),
                )
            )
            raise
        except Exception as exc:
            now = _now()
            job.job_status = JobStatus.FAILED
            job.job_error = JobError(
                code=type(exc).__name__,
                message=str(exc),
            )
            job.job_stage = Stage3CodexRunFailed(
                updated_at=now,
                data=Stage3CodexRunFailedData(error=str(exc)),
            )
            job.finished_at = now
            job.updated_at = now
            await self.jobs.save(job)
            await self.job_events.append(
                Event4CodexRunFailed(
                    created_at=now,
                    payload=Event4CodexRunFailedPayload(
                        job_id_issuer=job.job_id,
                        error=str(exc),
                    ),
                )
            )
            raise

    async def _store_diagnostic_artifacts(
        self,
        job: Job,
        exec_result: CodexExecResult,
    ) -> None:
        """Persist diagnostic artifacts captured while Codex ran."""
        for artifact in exec_result.diagnostic_artifacts():
            await self._store_artifact(
                job=job,
                content=artifact.content,
                name=artifact.filename,
                role=ArtifactRole.LOG,
                kind=ArtifactKind.TEXT,
                metadata=artifact.metadata,
            )

    async def _store_codex_output(
        self,
        job: Job,
        exec_result: CodexExecResult,
    ) -> JobArtifact | None:
        """Persist the final Codex output artifact when it exists."""
        if not exec_result.output_text:
            return None
        return await self._store_artifact(
            job=job,
            content=exec_result.output_text.encode(),
            name="codex_result.txt",
            role=ArtifactRole.OUTPUT,
            kind=ArtifactKind.TEXT,
            metadata={"filename": "codex_result.txt", "source": "codex"},
        )

    async def _store_artifact(
        self,
        *,
        job: Job,
        content: bytes | Path,
        name: str,
        role: ArtifactRole,
        kind: ArtifactKind,
        metadata: dict,
        description: str | None = None,
    ) -> JobArtifact:
        location = await self.storage.write(
            content=content,
            metadata=metadata,
        )
        artifact = JobArtifact(
            artifact_id=uuid4(),
            job_id=job.job_id,
            name=name,
            description=description,
            role=role,
            kind=kind,
            location=location,
            metadata=metadata,
            created_at=_now(),
        )
        await self.artifacts.create(artifact)
        await self.job_events.append(
            Event2CodexRunArtifactCreated(
                created_at=_now(),
                payload=Event2CodexRunArtifactCreatedPayload(
                    job_id_issuer=job.job_id,
                    artifact_id=str(artifact.artifact_id),
                    filename=name,
                ),
            )
        )
        return artifact

    async def _collect_generated_artifacts(
        self,
        *,
        job: Job,
        job_workspace: Path,
    ) -> list[JobArtifact]:
        """Persist all files generated in this Codex run directory."""
        generated_artifacts: list[JobArtifact] = []
        for path in list(_iter_files(job_workspace)):
            relative_path = path.relative_to(job_workspace)
            artifact = await self._store_artifact(
                job=job,
                content=path,
                name=str(relative_path),
                role=ArtifactRole.OUTPUT,
                kind=ArtifactKind.FILE,
                metadata={
                    "filename": path.name,
                    "relative_path": str(relative_path),
                    "source": "codex",
                },
                description="Codex workspace file",
            )
            generated_artifacts.append(artifact)
        return generated_artifacts

    def _job_workspace(self, job: Job) -> Path:
        """Return the workspace for a Codex run job."""
        job_input = job.job_input or {}
        workdir = job_input.get("workdir")
        workspace_root = self.default_working_directory
        if isinstance(workdir, str) and workdir:
            workspace_root = Path(workdir)
        return workspace_root / str(job.job_id)


def new_codex_run_job_use_case(
    jobs: JobRepository,
    artifacts: JobArtifactRepository,
    storage: ArtifactStorage,
    job_events: JobEventRepository,
    codex_executor: CodexExecutor,
    default_working_directory: Path,
) -> CodexRunJobUseCase:
    """Instantiate the Codex run job use case."""
    return CodexRunJobUseCaseImpl(
        jobs=jobs,
        artifacts=artifacts,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=default_working_directory,
    )


def _job_prompt(job: Job) -> str:
    """Return the prompt for a Codex run job."""
    job_input = job.job_input or {}
    prompt = job_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("codex_run job requires input.prompt")
    return prompt


def _iter_files(root: Path) -> Iterable[Path]:
    """Yield regular files under a root directory."""
    return (path for path in root.rglob("*") if path.is_file())


def _now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(UTC)
