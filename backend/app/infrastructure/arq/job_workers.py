"""ARQ worker bindings for job contracts."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from functools import wraps
from typing import Any, TypeVar, cast, get_type_hints
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession

from app.domain.job import JobContract, JobError, UnknownJobContractError, get_job_class
from app.infrastructure.arq.deps import get_arq_db_engine, new_arq_job_repository

ResultT = TypeVar("ResultT")

type ArqWorkerFunction[ResultT] = Callable[..., Awaitable[ResultT]]
type ExecutableJobContract = type[JobContract[Any, Any]]


class JobWorkerBindingRegistry:
    """Map job contracts to ARQ worker functions."""

    def __init__(self, *, package: str | None = None) -> None:
        """Create an optionally package-backed worker registry."""
        self.package = package
        self._loaded = package is None
        self._bindings: dict[tuple[str, str], Callable] = {}

    def register(
        self,
        function: ArqWorkerFunction[ResultT],
    ) -> ArqWorkerFunction[ResultT | None]:
        """Register a worker function for a contract."""
        contract = _contract_from_worker(function)
        if get_job_class(type=contract.type, version=contract.version) is None:
            raise UnknownJobContractError(
                f"Unknown job contract: {contract.type} {contract.version}"
            )
        wrapped = _claim_running_before_execute(function, contract)
        self._bindings[(contract.type, contract.version)] = wrapped
        return wrapped

    def get(self, *, type: str, version: str) -> Callable | None:
        """Return a worker function for a contract, if one is bound."""
        self.ensure_loaded()
        return self._bindings.get((type, version))

    def functions(self) -> list[Callable]:
        """Return registered ARQ worker functions."""
        self.ensure_loaded()
        return list(dict.fromkeys(self._bindings.values()))

    def ensure_loaded(self) -> None:
        """Import the configured worker package once so decorators can register."""
        if self._loaded:
            return
        assert self.package is not None
        self._loaded = True
        importlib.import_module(self.package)


worker_bindings = JobWorkerBindingRegistry(package="app.infrastructure.arq.jobs")


def job_worker[ResultT](
    function: ArqWorkerFunction[ResultT],
) -> ArqWorkerFunction[ResultT | None]:
    """Decorate an ARQ worker function with its annotated job entity."""
    return worker_bindings.register(function)


def _claim_running_before_execute[ResultT](
    function: ArqWorkerFunction[ResultT],
    contract: ExecutableJobContract,
) -> ArqWorkerFunction[ResultT | None]:
    @wraps(function)
    async def wrapped(ctx: dict[str, Any], job_id: str, *args: Any, **kwargs: Any):
        parsed_job_id = UUID(job_id)
        if not await _claim_execution(ctx, parsed_job_id):
            return None
        try:
            job = await _load_job(ctx, parsed_job_id, contract)
            result = await function(ctx, job, *args, **kwargs)
        except asyncio.CancelledError:
            await _mark_cancelled(ctx, parsed_job_id)
            raise
        except Exception as exc:
            await _mark_failed(ctx, parsed_job_id, exc)
            raise
        await _mark_succeeded(ctx, parsed_job_id, result)
        return result

    return wrapped


async def _claim_execution(ctx: dict[str, Any], job_id: UUID) -> bool:
    return await _with_job_repository(
        ctx,
        lambda jobs: jobs.try_mark_running(
            job_id,
            started_at=datetime.now(UTC),
        ),
    )


async def _load_job(
    ctx: dict[str, Any],
    job_id: UUID,
    contract: ExecutableJobContract,
) -> JobContract[Any, Any]:
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        jobs = new_arq_job_repository(session)
        job = await jobs.get(job_id)
        if not isinstance(job, contract):
            raise ValueError(
                f"Expected {contract.type} {contract.version}, "
                f"got {job.type} {job.version}"
            )
        return cast(JobContract[Any, Any], job)


def _contract_from_worker(function: ArqWorkerFunction) -> ExecutableJobContract:
    hints = get_type_hints(function)
    contract = hints.get("job")
    if not isinstance(contract, type) or not issubclass(contract, JobContract):
        raise TypeError(
            f"{getattr(function, '__name__', repr(function))} must annotate "
            "its job argument with a JobContract"
        )
    return contract


async def _mark_succeeded(ctx: dict[str, Any], job_id: UUID, result: object) -> bool:
    return await _with_job_repository(
        ctx,
        lambda jobs: jobs.try_mark_succeeded(
            job_id,
            result=result,
            finished_at=datetime.now(UTC),
        ),
    )


async def _mark_failed(ctx: dict[str, Any], job_id: UUID, exc: Exception) -> bool:
    return await _with_job_repository(
        ctx,
        lambda jobs: jobs.try_mark_failed(
            job_id,
            error=JobError(code=type(exc).__name__, message=str(exc)),
            finished_at=datetime.now(UTC),
        ),
    )


async def _mark_cancelled(ctx: dict[str, Any], job_id: UUID) -> bool:
    return await _with_job_repository(
        ctx,
        lambda jobs: jobs.try_mark_cancelled(
            job_id,
            error=JobError(code="CancelledError", message="Job cancelled"),
            finished_at=datetime.now(UTC),
        ),
    )


async def _with_job_repository(ctx: dict[str, Any], operation) -> bool:
    engine = get_arq_db_engine(ctx)
    async with AsyncSession(engine) as session:
        try:
            jobs = new_arq_job_repository(session)
            result = await operation(jobs)
            await session.commit()
            return result
        except Exception:
            await session.rollback()
            raise
