"""ARQ job worker binding tests."""

import asyncio
from datetime import UTC, datetime
from types import ModuleType
from typing import Any, cast

import pytest

from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobId,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import CodexAuthInputV1, CodexAuthJobV1
from app.domain.job.codex_run_job_use_case import (
    CodexRunInputV1,
    CodexRunJobV1,
    CodexRunOutput,
)
from app.infrastructure.arq.deps import ARQ_DB_ENGINE
from app.infrastructure.arq.job_workers import JobWorkerBindingRegistry
from app.infrastructure.sqlmodel.job import JobDTO, new_job_repository

pytestmark = pytest.mark.anyio


async def test_worker_binding_marks_job_succeeded_after_execute(db_session) -> None:
    registry = JobWorkerBindingRegistry()
    called: list[str] = []

    async def dummy_worker(_ctx, job: CodexRunJobV1) -> CodexRunOutput:
        called.append(str(job.id))
        return CodexRunOutput(output_file_id=None, log_files=1, generated_files=2)

    wrapped = registry.register(dummy_worker)
    job = _codex_run_job(status=JobStatus.QUEUED)
    await new_job_repository(db_session).create(job)
    await db_session.commit()

    result = await wrapped({ARQ_DB_ENGINE: db_session.bind}, str(job.id))

    db_session.expire_all()
    row = await db_session.get(JobDTO, job.id.value)
    assert result == CodexRunOutput(output_file_id=None, log_files=1, generated_files=2)
    assert cast(Any, wrapped).__name__ == "dummy_worker"
    assert called == [str(job.id)]
    assert row is not None
    assert row.status == JobStatus.SUCCEEDED.value
    assert row.started_at is not None
    assert row.finished_at is not None
    assert row.result == {"output_file_id": None, "log_files": 1, "generated_files": 2}


async def test_worker_binding_marks_job_failed_when_execute_raises(db_session) -> None:
    registry = JobWorkerBindingRegistry()

    async def dummy_worker(_ctx, job: CodexRunJobV1) -> CodexRunOutput:
        assert job.id
        raise RuntimeError("boom")

    wrapped = registry.register(dummy_worker)
    job = _codex_run_job(status=JobStatus.QUEUED)
    await new_job_repository(db_session).create(job)
    await db_session.commit()

    with pytest.raises(RuntimeError, match="boom"):
        await wrapped({ARQ_DB_ENGINE: db_session.bind}, str(job.id))

    db_session.expire_all()
    row = await db_session.get(JobDTO, job.id.value)
    assert row is not None
    assert row.status == JobStatus.FAILED.value
    assert row.finished_at is not None
    assert row.error == {
        "code": "RuntimeError",
        "message": "boom",
        "details": {},
        "retryable": False,
    }


async def test_worker_binding_marks_job_cancelled_when_execute_is_cancelled(
    db_session,
) -> None:
    registry = JobWorkerBindingRegistry()

    async def dummy_worker(_ctx, job: CodexRunJobV1) -> CodexRunOutput:
        assert job.id
        raise asyncio.CancelledError

    wrapped = registry.register(dummy_worker)
    job = _codex_run_job(status=JobStatus.QUEUED)
    await new_job_repository(db_session).create(job)
    await db_session.commit()

    with pytest.raises(asyncio.CancelledError):
        await wrapped({ARQ_DB_ENGINE: db_session.bind}, str(job.id))

    db_session.expire_all()
    row = await db_session.get(JobDTO, job.id.value)
    assert row is not None
    assert row.status == JobStatus.CANCELLED.value
    assert row.finished_at is not None
    assert row.error == {
        "code": "CancelledError",
        "message": "Job cancelled",
        "details": {},
        "retryable": False,
    }


async def test_worker_binding_skips_execute_when_claim_fails(db_session) -> None:
    registry = JobWorkerBindingRegistry()
    called: list[str] = []

    async def dummy_worker(_ctx, job: CodexRunJobV1) -> CodexRunOutput:
        called.append(str(job.id))
        return CodexRunOutput(output_file_id=None, log_files=1, generated_files=2)

    wrapped = registry.register(dummy_worker)
    job = _codex_run_job(status=JobStatus.CANCELLED)
    await new_job_repository(db_session).create(job)
    await db_session.commit()

    result = await wrapped({ARQ_DB_ENGINE: db_session.bind}, str(job.id))

    db_session.expire_all()
    row = await db_session.get(JobDTO, job.id.value)
    assert result is None
    assert called == []
    assert row is not None
    assert row.status == JobStatus.CANCELLED.value


async def test_worker_binding_fails_job_when_contract_does_not_match(db_session) -> None:
    registry = JobWorkerBindingRegistry()
    called: list[str] = []

    async def dummy_worker(_ctx, job: CodexRunJobV1) -> CodexRunOutput:
        called.append(str(job.id))
        return CodexRunOutput(output_file_id=None, log_files=1, generated_files=2)

    wrapped = registry.register(dummy_worker)
    job = _codex_auth_job(status=JobStatus.QUEUED)
    await new_job_repository(db_session).create(job)
    await db_session.commit()

    with pytest.raises(ValueError, match="Expected execute_codex_run_job_use_case v1"):
        await wrapped({ARQ_DB_ENGINE: db_session.bind}, str(job.id))

    db_session.expire_all()
    row = await db_session.get(JobDTO, job.id.value)
    assert called == []
    assert row is not None
    assert row.status == JobStatus.FAILED.value
    assert row.error is not None
    assert row.error["code"] == "ValueError"
    assert "Expected execute_codex_run_job_use_case v1" in row.error["message"]


def test_worker_binding_registry_loads_configured_package_once(monkeypatch) -> None:
    calls: list[str] = []
    module = ModuleType("test_worker_package")

    def fake_import_module(name: str):
        calls.append(name)
        return module

    monkeypatch.setattr(
        "app.infrastructure.arq.job_workers.importlib.import_module",
        fake_import_module,
    )
    registry = JobWorkerBindingRegistry(package="test_worker_package")

    assert registry.functions() == []
    assert registry.get(type="missing", version="v1") is None

    assert calls == ["test_worker_package"]


def _codex_run_job(*, status: JobStatus) -> Job:
    now = datetime(2026, 7, 7, tzinfo=UTC)
    return CodexRunJobV1(
        id=JobId.generate(),
        type=CodexRunJobV1.type,
        version=CodexRunJobV1.version,
        name="Codex run worker",
        description=None,
        input=CodexRunInputV1(prompt="run"),
        result=None,
        status=status,
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )


def _codex_auth_job(*, status: JobStatus) -> Job:
    now = datetime(2026, 7, 7, tzinfo=UTC)
    return CodexAuthJobV1(
        id=JobId.generate(),
        type=CodexAuthJobV1.type,
        version=CodexAuthJobV1.version,
        name="Codex auth worker",
        description=None,
        input=CodexAuthInputV1(),
        result=None,
        status=status,
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=None,
        finished_at=None,
        error=None,
    )
