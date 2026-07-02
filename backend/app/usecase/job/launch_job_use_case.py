"""Provide a compatibility use case for launching known jobs."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import Initiator, Job, JobRepository, JobStatus
from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1, CodexAuthJobV1
from app.domain.job.codex_run_job_use_case import CodexRunInputV1, CodexRunJobV1
from app.usecase.job.job_launcher import JobLauncher, new_job_launcher
from app.usecase.job.ports import JobQueue


class LaunchJobUseCase(ABC):
    """Define the application boundary for launching jobs."""

    @abstractmethod
    async def execute(
        self,
        job_type: str,
        job_name: str,
        root_initiator: Initiator,
        job_description: str | None = None,
        job_input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job and durable dispatch intent."""


class LaunchJobUseCaseImpl(LaunchJobUseCase):
    """Build a typed job contract and delegate to JobLauncher."""

    def __init__(
        self,
        jobs: JobRepository,
        queue: JobQueue | None = None,
        launcher: JobLauncher | None = None,
    ):
        """Store use case dependencies."""
        self.jobs = jobs
        self.queue = queue
        self.launcher = launcher or new_job_launcher(jobs=jobs)

    async def execute(
        self,
        job_type: str,
        job_name: str,
        root_initiator: Initiator,
        job_description: str | None = None,
        job_input: dict | None = None,
        parent_job_id: UUID | None = None,
    ) -> UUID:
        """Create a queued job and durable dispatch intent."""
        job = _new_job(
            job_type=job_type,
            job_name=job_name,
            root_initiator=root_initiator,
            job_description=job_description,
            job_input=job_input,
            parent_job_id=parent_job_id,
        )
        if job.type not in {CodexRunJobV1.type, CodexAuthJobV1.type}:
            await self.jobs.create(job)
            if self.queue is not None:
                await self.queue.enqueue(job_type=job.job_type, job_id=job.id)
            return job.id

        job_id = await self.launcher.launch(job)

        # Compatibility fallback for in-memory tests and adapters that do not pass a
        # SQL session-backed launcher yet. Production launchers write outbox rows.
        if self.queue is not None and getattr(self.launcher, "session", None) is None:
            await self.queue.enqueue(job_type=job.job_type, job_id=job.id)
        return job_id


def new_launch_job_use_case(
    jobs: JobRepository,
    queue: JobQueue,
    session: AsyncSession | None = None,
) -> LaunchJobUseCase:
    """Instantiate the launch job use case."""
    return LaunchJobUseCaseImpl(
        jobs=jobs,
        queue=queue,
        launcher=new_job_launcher(jobs=jobs, session=session),
    )


def _new_job(
    *,
    job_type: str,
    job_name: str,
    root_initiator: Initiator,
    job_description: str | None,
    job_input: dict | None,
    parent_job_id: UUID | None,
):
    normalized_type = job_type.replace("_", ".")
    if normalized_type == CodexRunJobV1.type:
        return CodexRunJobV1.new(
            initiator=root_initiator,
            input=CodexRunInputV1(**(job_input or {})),
            name=job_name,
            description=job_description,
            parent_job_id=parent_job_id,
        )
    if normalized_type == CodexAuthJobV1.type:
        return CodexAuthJobV1.new(
            initiator=root_initiator,
            input=CodexAuthInputV1(**(job_input or {})),
            name=job_name,
            description=job_description,
            parent_job_id=parent_job_id,
        )
    now = datetime.now(UTC)
    return Job(
        id=uuid4(),
        type=job_type,
        version="v1",
        name=job_name,
        description=job_description,
        input=job_input,
        result=None,
        status=JobStatus.QUEUED,
        initiator=root_initiator,
        parent_job_id=parent_job_id,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )
