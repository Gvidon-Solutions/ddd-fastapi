"""Define the job queue port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class JobQueue(ABC):
    """Enqueue jobs without exposing a concrete queue implementation."""

    @abstractmethod
    async def enqueue(
        self,
        job_type: str,
        job_id: UUID,
    ) -> None:
        """Enqueue a job for asynchronous execution."""

    @abstractmethod
    async def cancel(self, job_id: UUID) -> bool:
        """Cancel an enqueued or running asynchronous job."""
