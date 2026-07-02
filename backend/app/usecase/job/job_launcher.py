"""Launch typed jobs through a durable dispatch outbox."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import Job, JobRepository, job_registry
from app.domain.job.base.entities import JobDispatchOutbox, JobDispatchOutboxStatus
from app.infrastructure.sqlmodel.job.job_dispatch_outbox_dto import (
    JobDispatchOutboxDTO,
)


class JobLauncher(ABC):
    """Application boundary for launching already constructed typed jobs."""

    @abstractmethod
    async def launch(self, job: Job) -> UUID:
        """Persist a queued job and a durable dispatch intent."""


class JobLauncherImpl(JobLauncher):
    """Persist jobs with durable dispatch intent."""

    def __init__(
        self,
        jobs: JobRepository,
        session: AsyncSession | None = None,
    ) -> None:
        """Store launcher dependencies."""
        self.jobs = jobs
        self.session = session

    async def launch(self, job: Job) -> UUID:
        """Persist a queued job and a durable dispatch intent."""
        job_registry.get(type=job.type, version=job.version)
        await self.jobs.create(job)

        if self.session is not None:
            now = datetime.now(UTC)
            self.session.add(
                JobDispatchOutboxDTO.from_entity(
                    JobDispatchOutbox(
                        outbox_id=uuid4(),
                        job_id=job.id,
                        type=job.type,
                        version=job.version,
                        status=JobDispatchOutboxStatus.PENDING,
                        attempts=0,
                        next_attempt_at=now,
                        last_error=None,
                        created_at=now,
                        updated_at=now,
                        dispatched_at=None,
                    )
                )
            )
        return job.id


def new_job_launcher(
    jobs: JobRepository,
    session: AsyncSession | None = None,
) -> JobLauncher:
    """Create a job launcher."""
    return JobLauncherImpl(jobs=jobs, session=session)
