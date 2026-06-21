"""Codex job event publisher port."""

from abc import ABC, abstractmethod

from app.domain.codex_job.value_objects import CodexJobId


class CodexJobEventPublisher(ABC):
    """Publish streaming events produced by a Codex job."""

    @abstractmethod
    async def publish(
        self,
        codex_job_id: CodexJobId,
        event_type: str,
        payload: str,
    ) -> None:
        """Publish one Codex job event."""
