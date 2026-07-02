"""Job cancellation backend port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID


class JobCancellationBackend(ABC):
    """Track cancellation requests for running jobs."""

    @abstractmethod
    async def request_cancel(self, job_id: UUID) -> None:
        """Request cancellation for a running job."""

    @abstractmethod
    async def is_cancel_requested(self, job_id: UUID) -> bool:
        """Return whether cancellation was requested."""

    @abstractmethod
    async def clear_cancel_request(self, job_id: UUID) -> None:
        """Clear the cancellation request."""
