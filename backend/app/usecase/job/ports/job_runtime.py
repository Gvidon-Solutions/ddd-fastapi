"""Define the external job runtime port."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.job import JobId


class JobRuntime(ABC):
    """Run, cancel, and track externally executed jobs."""

    @abstractmethod
    async def enqueue(
        self,
        job_type: str,
        job_id: JobId,
    ) -> None:
        """Enqueue a job for asynchronous execution."""

    @abstractmethod
    async def cancel(self, job_id: JobId) -> bool:
        """Cancel an enqueued or running asynchronous job."""

    @abstractmethod
    async def request_cancel(self, job_id: JobId) -> None:
        """Request cooperative cancellation for a running job."""

    @abstractmethod
    async def is_cancel_requested(self, job_id: JobId) -> bool:
        """Return whether cooperative cancellation was requested."""

    @abstractmethod
    async def clear_cancel_request(self, job_id: JobId) -> None:
        """Clear the cooperative cancellation request."""

    @abstractmethod
    async def await_terminal(
        self,
        job_id: JobId,
        *,
        timeout_seconds: float | None = None,
        poll_delay_seconds: float = 0.5,
    ) -> object:
        """Wait until the external job reaches a terminal runtime state."""
