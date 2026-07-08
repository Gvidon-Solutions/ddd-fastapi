"""Job event realtime stream port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass

from app.domain.job import JobId


@dataclass(frozen=True)
class JobEventStreamMessage:
    """Represent one event message read from a job event stream."""

    stream_id: str
    event: dict[str, object]


class JobEventStream(ABC):
    """Read realtime events emitted for one job."""

    @abstractmethod
    def listen(
        self,
        job_id: JobId,
        *,
        last_event_id: str = "0-0",
    ) -> AsyncIterator[JobEventStreamMessage]:
        """Yield event messages for one job from a stream position."""
