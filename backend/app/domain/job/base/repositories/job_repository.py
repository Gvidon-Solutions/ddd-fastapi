"""Define the Job repository contract."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.job.base.entities import AnyJob, Job, JobEvent, JobFile
from app.domain.job.base.value_objects import JobError, JobFileRole
from app.domain.job.base.value_objects.job_details import JobDetails
from app.domain.job.base.value_objects.job_execution_record import JobExecutionRecord
from app.domain.job.base.value_objects.job_summary import JobSummary


class JobRepository(ABC):
    """Persist jobs."""

    @abstractmethod
    async def create(self, job: Job) -> None:
        """Create a new job."""

    @abstractmethod
    async def get(self, job_id: UUID) -> AnyJob:
        """Return a job by ID."""

    @abstractmethod
    async def get_detail(self, job_id: UUID) -> JobDetails:
        """Return a job details value object."""

    @abstractmethod
    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return job summaries created by an initiator external id."""

    @abstractmethod
    async def add_file(self, job_file: JobFile) -> None:
        """Associate a file with a job."""

    @abstractmethod
    async def list_files(
        self,
        job_id: UUID,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files associated with a job."""

    @abstractmethod
    async def append_event(self, job_id: UUID, event: JobEvent) -> None:
        """Append a new job event."""

    @abstractmethod
    async def list_events(self, job_id: UUID) -> list[JobEvent]:
        """Return events emitted by a job."""

    @abstractmethod
    async def save(self, job: Job) -> None:
        """Persist changes to an existing job."""

    async def get_execution_record(self, job_id: UUID) -> JobExecutionRecord:
        """Return raw execution data without typed deserialization."""
        raise NotImplementedError

    async def try_mark_running(
        self,
        job_id: UUID,
        *,
        started_at: datetime,
    ) -> bool:
        """Atomically mark a queued job as running."""
        raise NotImplementedError

    async def try_mark_succeeded(
        self,
        job_id: UUID,
        *,
        result: object,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as succeeded."""
        raise NotImplementedError

    async def try_mark_failed(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running job as failed."""
        raise NotImplementedError

    async def try_mark_cancelled(
        self,
        job_id: UUID,
        *,
        error: JobError,
        finished_at: datetime,
    ) -> bool:
        """Atomically mark a running or queued job as cancelled."""
        raise NotImplementedError

    async def delete(self, job_id: UUID, *, cascade_children: bool = False) -> None:
        """Delete a terminal job and clean up links/read-side metadata."""
        raise NotImplementedError
