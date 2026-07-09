"""Await terminal job status application use case."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from app.domain.job import (
    JobAwaitTimeoutError,
    JobDetails,
    JobId,
    JobNotFoundError,
    JobReadAccessDeniedError,
    JobReadNotFoundError,
    JobRepository,
    JobStatus,
)
from app.domain.user.value_objects import UserId

type Sleep = Callable[[float], Awaitable[None]]
type Monotonic = Callable[[], float]


class AwaitJobTerminalUseCase(ABC):
    """Define the application boundary for awaiting one terminal job."""

    @abstractmethod
    async def execute(
        self,
        job_id: JobId,
        *,
        current_user_id: UserId,
        timeout_seconds: float = 300.0,
        initial_poll_delay_seconds: float = 0.25,
        max_poll_delay_seconds: float = 2.0,
    ) -> JobDetails:
        """Wait until the job reaches a terminal durable status."""


class AwaitJobTerminalUseCaseImpl(AwaitJobTerminalUseCase):
    """Await a terminal durable job status using lightweight DB polling."""

    def __init__(
        self,
        jobs: JobRepository,
        *,
        sleep: Sleep = asyncio.sleep,
        monotonic: Monotonic = time.monotonic,
    ) -> None:
        """Store use case dependencies."""
        self.jobs = jobs
        self.sleep = sleep
        self.monotonic = monotonic

    async def execute(
        self,
        job_id: JobId,
        *,
        current_user_id: UserId,
        timeout_seconds: float = 300.0,
        initial_poll_delay_seconds: float = 0.25,
        max_poll_delay_seconds: float = 2.0,
    ) -> JobDetails:
        """Wait until the job reaches a terminal durable status."""
        try:
            job = await self.jobs.get(job_id)
        except JobNotFoundError as error:
            raise JobReadNotFoundError(str(job_id)) from error

        if job.initiator.external_id != str(current_user_id):
            raise JobReadAccessDeniedError(str(job_id))
        if job.status in _TERMINAL_STATUSES:
            return await self._get_details(job_id)

        deadline = self.monotonic() + timeout_seconds
        delay = max(0.0, initial_poll_delay_seconds)
        max_delay = max(delay, max_poll_delay_seconds)

        while True:
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise JobAwaitTimeoutError(str(job_id))

            await self.sleep(min(delay, remaining))
            status = await self._get_status(job_id)
            if status in _TERMINAL_STATUSES:
                return await self._get_details(job_id)
            delay = min(max_delay, delay * 2 if delay > 0 else max_delay)

    async def _get_status(self, job_id: JobId) -> JobStatus:
        try:
            return await self.jobs.get_status(job_id)
        except JobNotFoundError as error:
            raise JobReadNotFoundError(str(job_id)) from error

    async def _get_details(self, job_id: JobId) -> JobDetails:
        try:
            return await self.jobs.get_detail(job_id)
        except JobNotFoundError as error:
            raise JobReadNotFoundError(str(job_id)) from error


def new_await_job_terminal_use_case(
    jobs: JobRepository,
) -> AwaitJobTerminalUseCase:
    """Instantiate the await-job-terminal use case."""
    return AwaitJobTerminalUseCaseImpl(jobs=jobs)


_TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
