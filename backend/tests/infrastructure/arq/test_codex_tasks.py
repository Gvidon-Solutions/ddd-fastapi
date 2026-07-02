"""Codex ARQ task tests."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.domain.job import (
    ActorType,
    FileKind,
    FileStatus,
    Initiator,
    Job,
    JobError,
    JobEvent,
    JobEventRepository,
    JobFile,
    JobFileRepository,
    JobFileRole,
    JobRepository,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthInputV1,
    CodexAuthJobResult,
    CodexAuthResult,
    CodexDeviceAuth,
)
from app.domain.job.codex_run_job_use_case import CodexRunInputV1
from app.infrastructure.file_storage import FilesystemFileStorage
from app.usecase.job.codex import (
    CodexAuthenticator,
    CodexExecResult,
    new_codex_auth_use_case,
    new_codex_run_job_use_case,
)

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self, job: Job):
        self.jobs = {job.id: job}

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job


class FakeJobFileRepository(JobFileRepository):
    """Store job files in memory."""

    def __init__(self) -> None:
        self.files: list[JobFile] = []

    async def create(self, job_file: JobFile) -> None:
        """Create a job-file association."""
        self.files.append(job_file)

    async def list_by_job(
        self,
        job_id: UUID,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files for a job."""
        files = [job_file for job_file in self.files if job_file.job_id == job_id]
        if role is not None:
            files = [job_file for job_file in files if job_file.role == role]
        return files


class FakeJobEventRepository(JobEventRepository):
    """Store events in memory."""

    def __init__(self) -> None:
        self.events: list[tuple[UUID, JobEvent]] = []

    async def append(self, job_id: UUID, event: JobEvent) -> None:
        """Append an event."""
        self.events.append((job_id, event))

    async def list_by_job(self, job_id: UUID) -> list[JobEvent]:
        """Return events for a job."""
        return [event for event_job_id, event in self.events if event_job_id == job_id]


class FakeCodexAuthenticator(CodexAuthenticator):
    """Return fixed Codex auth data."""

    def __init__(self, *, cancel_on_wait: bool = False) -> None:
        self.cancel_on_wait = cancel_on_wait
        self.cancelled = False

    async def start_device_auth(self) -> CodexDeviceAuth:
        """Start fake device auth."""
        return CodexDeviceAuth(
            verification_url="https://auth.openai.com/device",
            device_code="ABCD-EFGH",
        )

    async def await_for_user_login(self) -> CodexAuthResult:
        """Wait for fake user login."""
        if self.cancel_on_wait:
            raise asyncio.CancelledError
        return CodexAuthResult(authenticated=True)

    async def cancel(self) -> bool:
        """Cancel fake auth."""
        self.cancelled = True
        return True


class FakeCodexExecutor:
    """Return fixed Codex exec data."""

    def __init__(self, *, cancel_on_exec: bool = False) -> None:
        self.prompt: str | None = None
        self.workdir: Path | None = None
        self.cancel_on_exec = cancel_on_exec
        self.cancelled = False

    async def codex_exec(
        self,
        *,
        prompt: str,
        workdir: Path,
    ) -> CodexExecResult:
        """Execute fake Codex."""
        self.prompt = prompt
        self.workdir = workdir
        workdir.mkdir(parents=True, exist_ok=True)
        (workdir / "changed.py").write_text("print('changed')\n")
        if self.cancel_on_exec:
            raise asyncio.CancelledError
        return CodexExecResult(
            return_code=0,
            output="Codex result",
            stdout_lines=['{"type":"message","message":"running"}'],
            stderr_lines=["warning"],
        )

    async def cancel(self) -> bool:
        """Cancel fake Codex exec."""
        self.cancelled = True
        return True


def _job(
    job_type: str,
    job_input: object | None = None,
) -> Job:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    return Job(
        id=uuid4(),
        type=job_type,
        version="v1",
        name=job_type,
        description=None,
        input=job_input,
        result=None,
        status=JobStatus.RUNNING,
        initiator=Initiator(type=ActorType.USER, external_id="anton"),
        parent_job_id=None,
        requested_at=now,
        updated_at=now,
        started_at=now,
        finished_at=None,
        error=None,
    )


async def test_codex_auth_stores_result_without_durable_login_code() -> None:
    job = _job("codex.auth", CodexAuthInputV1())
    jobs = FakeJobRepository(job)
    job_events = FakeJobEventRepository()
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=FakeCodexAuthenticator(),
    )

    result = await use_case.execute(job.id)

    assert job.status == JobStatus.SUCCEEDED
    assert isinstance(result, CodexAuthJobResult)
    assert result.authenticated is True
    assert job.result == CodexAuthJobResult(authenticated=True)
    assert all(event.source == "codex_auth_job_use_case" for _, event in job_events.events)


async def test_codex_auth_cancellation_updates_job_and_kills_authenticator() -> None:
    job = _job("codex.auth", CodexAuthInputV1())
    jobs = FakeJobRepository(job)
    job_events = FakeJobEventRepository()
    authenticator = FakeCodexAuthenticator(cancel_on_wait=True)
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=authenticator,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job.id)

    assert authenticator.cancelled is True
    assert job.status == JobStatus.CANCELLED
    assert job.error == JobError(code="CancelledError", message="Job cancelled")
    assert job_events.events[-1][1].type == "CodexAuthCancelledV1"


async def test_codex_run_creates_output_and_log_files(tmp_path: Path) -> None:
    job = _job(
        "codex.run",
        CodexRunInputV1(
            prompt="Review repository",
            workdir=str(tmp_path / "workdir"),
        ),
    )
    jobs = FakeJobRepository(job)
    job_files = FakeJobFileRepository()
    storage = FilesystemFileStorage(root=tmp_path / "files")
    job_events = FakeJobEventRepository()
    codex_executor = FakeCodexExecutor()
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        job_files=job_files,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
    )

    summary = await use_case.execute(job.id)

    all_files = await job_files.list_by_job(job.id)
    output_files = await job_files.list_by_job(job.id, JobFileRole.OUTPUT)
    primary_files = await job_files.list_by_job(job.id, JobFileRole.PRIMARY_OUTPUT)
    log_files = await job_files.list_by_job(job.id, JobFileRole.LOG)
    files_by_name = {job_file.file.name: job_file for job_file in output_files + primary_files}
    assert job.status == JobStatus.SUCCEEDED
    assert summary["output_file_id"] == str(files_by_name["codex_result.txt"].file.file_id)
    assert summary["generated_files"] == 1
    assert summary["log_files"] == 2
    assert len(all_files) == 4
    assert len(output_files) == 1
    assert len(primary_files) == 1
    assert len(log_files) == 2
    assert all(job_file.file.kind in {FileKind.FILE, FileKind.TEXT} for job_file in all_files)
    assert all(job_file.file.status == FileStatus.ACTIVE for job_file in all_files)
    assert await storage.read(files_by_name["codex_result.txt"].file.location) == b"Codex result"
    assert await storage.read(files_by_name["changed.py"].file.location) == b"print('changed')\n"
    assert codex_executor.prompt == "Review repository"
    assert codex_executor.workdir == tmp_path / "workdir" / str(job.id)


async def test_codex_run_cancellation_updates_job_and_kills_executor(
    tmp_path: Path,
) -> None:
    job = _job(
        "codex.run",
        CodexRunInputV1(
            prompt="Review repository",
            workdir=str(tmp_path / "workdir"),
        ),
    )
    jobs = FakeJobRepository(job)
    job_files = FakeJobFileRepository()
    storage = FilesystemFileStorage(root=tmp_path / "files")
    job_events = FakeJobEventRepository()
    codex_executor = FakeCodexExecutor(cancel_on_exec=True)
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        job_files=job_files,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job.id)

    assert codex_executor.cancelled is True
    assert job.status == JobStatus.CANCELLED
    assert job.error == JobError(code="CancelledError", message="Job cancelled")
    assert job_events.events[-1][1].type == "CodexRunCancelledV1"
