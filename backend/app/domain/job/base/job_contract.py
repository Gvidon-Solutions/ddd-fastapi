"""Versioned executable job contract base class."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TypeVar
from uuid import UUID, uuid4

from app.domain.job.base.entities import Job
from app.domain.job.base.value_objects import Initiator, JobStatus

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


class JobContract[InputT, ResultT]:
    """Describe the input/result contract for one executable job version."""

    type: str
    version: str
    input: type[InputT]
    result: type[ResultT]

    @classmethod
    def new(
        cls,
        *,
        initiator: Initiator,
        input: InputT,
        name: str | None = None,
        description: str | None = None,
        parent_job_id: UUID | None = None,
    ) -> Job[InputT, ResultT]:
        """Create a queued job instance for this contract."""
        if not isinstance(input, cls.input):
            raise TypeError(f"{cls.type} {cls.version} requires {cls.input.__name__}")

        now = datetime.now(UTC)
        return Job(
            id=uuid4(),
            type=cls.type,
            version=cls.version,
            name=name,
            description=description,
            input=input,
            result=None,
            status=JobStatus.QUEUED,
            initiator=initiator,
            parent_job_id=parent_job_id,
            requested_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            error=None,
        )
