"""Versioned executable job contract base class."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Self, TypeVar
from uuid import UUID, uuid4

from app.domain.job.base.entities.job import Job
from app.domain.job.base.value_objects import Initiator, JobStatus

InputT = TypeVar("InputT")
ResultT = TypeVar("ResultT")


class JobContract[InputT, ResultT](Job[InputT, ResultT]):
    """Describe and type one executable job version."""

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
    ) -> Self:
        """Create a pending job instance for this contract."""
        if not isinstance(input, cls.input):
            raise TypeError(f"{cls.type} {cls.version} requires {cls.input.__name__}")

        now = datetime.now(UTC)
        return cls(
            id=uuid4(),
            type=cls.type,
            version=cls.version,
            name=name,
            description=description,
            input=input,
            result=None,
            status=JobStatus.PENDING,
            initiator=initiator,
            parent_job_id=parent_job_id,
            requested_at=now,
            updated_at=now,
            started_at=None,
            finished_at=None,
            error=None,
            dispatch_attempts=0,
            next_dispatch_at=now,
            last_dispatch_error=None,
            dispatched_at=None,
        )
