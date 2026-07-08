"""Define the external job event publisher port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import JobEvent, JobId


class EventPublisher(ABC):
    """Publish job events to external subscribers."""

    @abstractmethod
    async def emit(self, job_id: JobId, event: JobEvent) -> None:
        """Publish one event emitted by a job."""
