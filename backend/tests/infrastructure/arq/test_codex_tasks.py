"""Codex ARQ task tests."""

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, cast

import pytest

from app.domain.file import FileKind, FileStatus
from app.domain.job import (
    ActorType,
    Initiator,
    Job,
    JobDetails,
    JobEvent,
    JobFile,
    JobFileRole,
    JobId,
    JobNotFoundError,
    JobRepository,
    JobStatus,
    JobSummary,
    new_job_id,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthFailedError,
    CodexAuthInputV1,
    CodexAuthJobV1,
    CodexAuthResult,
    CodexAuthSession,
    CodexAuthSessionRepository,
    CodexAuthSessionStatus,
    CodexDeviceAuth,
)
from app.domain.job.codex_run_job_use_case import (
    CodexRunInputV1,
    CodexRunJobV1,
    CodexRunOutput,
)
from app.infrastructure.file_storage import FilesystemFileStorage
from app.usecase.job.codex import (
    CodexAuthenticator,
    CodexExecOutputHandler,
    CodexExecOutputLine,
    CodexExecResult,
    CodexExecutor,
    new_codex_auth_use_case,
    new_codex_run_job_use_case,
)
from app.usecase.job.ports import EventPublisher

pytestmark = pytest.mark.anyio


class FakeJobRepository(JobRepository):
    """Store jobs in memory."""

    def __init__(self, job: Job):
        self.jobs = {job.id: job}
        self.files: list[JobFile] = []
        self.events: list[tuple[JobId, JobEvent]] = []

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.id] = job

    async def get(self, job_id: JobId) -> Job:
        """Return a job."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        return self.jobs[job_id]

    async def get_detail(self, job_id: JobId) -> JobDetails:
        """Return job detail."""
        _ = job_id
        raise NotImplementedError

    async def get_status(self, job_id: JobId) -> JobStatus:
        """Return job status."""
        if job_id not in self.jobs:
            raise JobNotFoundError(str(job_id))
        return self.jobs[job_id].status

    async def list_by_initiator(self, initiator_external_id: str) -> list[JobSummary]:
        """Return jobs by initiator."""
        return [
            JobSummary(
                id=job.id,
                type=job.type,
                version=job.version,
                name=job.name,
                status=job.status,
                initiator=job.initiator,
                parent_job_id=job.parent_job_id,
                requested_at=job.requested_at,
                updated_at=job.updated_at,
                started_at=job.started_at,
                finished_at=job.finished_at,
            )
            for job in self.jobs.values()
            if job.initiator.external_id == initiator_external_id
        ]

    async def list_children(self, parent_job_id: JobId) -> list[JobSummary]:
        """Return no child jobs."""
        _ = parent_job_id
        return []

    async def add_file(self, job_file: JobFile) -> None:
        """Associate a file with a job."""
        self.files.append(job_file)

    async def list_files(
        self,
        job_id: JobId,
        role: JobFileRole | None = None,
    ) -> list[JobFile]:
        """Return files for a job."""
        files = [job_file for job_file in self.files if job_file.job_id == job_id]
        if role is not None:
            files = [job_file for job_file in files if job_file.role == role]
        return files

    async def append_event(self, job_id: JobId, event: JobEvent) -> None:
        """Append an event."""
        self.events.append((job_id, event))

    async def list_events(self, job_id: JobId) -> list[JobEvent]:
        """Return events for a job."""
        return [event for event_job_id, event in self.events if event_job_id == job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.id] = job


class FakeEventPublisher(EventPublisher):
    """Record published job events in memory."""

    def __init__(self) -> None:
        self.events: list[tuple[JobId, JobEvent]] = []

    async def emit(self, job_id: JobId, event: JobEvent) -> None:
        """Record a published event."""
        self.events.append((job_id, event))


class FakeCodexAuthenticator(CodexAuthenticator):
    """Return fixed Codex auth data."""

    def __init__(
        self,
        *,
        cancel_on_wait: bool = False,
        auth_result: CodexAuthResult | None = None,
    ) -> None:
        self.cancel_on_wait = cancel_on_wait
        self.auth_result = auth_result
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
        return self.auth_result or CodexAuthResult(authenticated=True)

    async def cancel(self) -> bool:
        """Cancel fake auth."""
        self.cancelled = True
        return True


class FakeAuthSessionRepository(CodexAuthSessionRepository):
    """Store one fake Codex auth session."""

    def __init__(self) -> None:
        self.session: CodexAuthSession | None = None
        self.authenticated_job_id: JobId | None = None
        self.failed: tuple[JobId, str] | None = None
        self.cancelled: tuple[JobId, str] | None = None

    async def save_pending(
        self,
        *,
        job_id: JobId,
        verification_url: str | None,
        user_code: str | None,
        expires_at: datetime,
    ) -> None:
        """Persist pending login data."""
        now = datetime.now(UTC)
        self.session = CodexAuthSession(
            job_id=job_id,
            verification_url=verification_url,
            user_code=user_code,
            expires_at=expires_at,
            status=CodexAuthSessionStatus.PENDING,
            error=None,
            created_at=now,
            updated_at=now,
        )

    async def mark_authenticated(self, job_id: JobId) -> None:
        """Mark authenticated."""
        self.authenticated_job_id = job_id

    async def mark_failed(self, job_id: JobId, error: str) -> None:
        """Mark failed."""
        self.failed = (job_id, error)

    async def mark_cancelled(self, job_id: JobId, reason: str) -> None:
        """Mark cancelled."""
        self.cancelled = (job_id, reason)

    async def get(self, job_id: JobId) -> CodexAuthSession | None:
        """Return stored session."""
        if self.session is None or self.session.job_id != job_id:
            return None
        return self.session


class FakeCodexExecutor(CodexExecutor):
    """Return fixed Codex exec data."""

    def __init__(self, *, cancel_on_exec: bool = False) -> None:
        self.prompt: str | None = None
        self.workdir: Path | None = None
        self.cancel_on_exec = cancel_on_exec
        self.cancelled = False

    def is_running(self) -> bool:
        """Return whether fake Codex is running."""
        return False

    async def codex_exec(
        self,
        *,
        prompt: str | None = None,
        stdin: str | None = None,
        workdir: Path | None = None,
        command: Sequence[str] = (),
        images: Sequence[Path | str] = (),
        model: str | None = None,
        sandbox_mode: str | None = None,
        configs: Sequence[str] = (),
        enable: Sequence[str] = (),
        disable: Sequence[str] = (),
        profile: str | None = None,
        oss: bool = False,
        local_provider: str | None = None,
        add_dirs: Sequence[Path | str] = (),
        ephemeral: bool = False,
        ignore_user_config: bool = False,
        ignore_rules: bool = False,
        output_schema: Path | str | None = None,
        color: Literal["always", "never", "auto"] | None = None,
        json_output: bool = True,
        strict_config: bool = True,
        skip_git_repo_check: bool = True,
        dangerously_bypass_approvals_and_sandbox: bool = False,
        dangerously_bypass_hook_trust: bool = False,
        output_last_message_path: Path | str | None = None,
        extra_options: Sequence[str] = (),
        output_handler: CodexExecOutputHandler | None = None,
    ) -> CodexExecResult:
        """Execute fake Codex."""
        self.prompt = prompt
        self.workdir = workdir
        if output_handler is not None:
            await output_handler(
                CodexExecOutputLine(
                    channel="stdout",
                    line_number=1,
                    line='{"type":"message","message":"running"}',
                )
            )
        assert workdir is not None
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


def _codex_auth_job() -> CodexAuthJobV1:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    return CodexAuthJobV1(
        id=new_job_id(),
        type="execute_codex_auth_job_use_case",
        version="v1",
        name="execute_codex_auth_job_use_case",
        description=None,
        input=CodexAuthInputV1(),
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


def _codex_run_job(job_input: CodexRunInputV1) -> CodexRunJobV1:
    now = datetime(2026, 6, 23, tzinfo=UTC)
    return CodexRunJobV1(
        id=new_job_id(),
        type="execute_codex_run_job_use_case",
        version="v1",
        name="execute_codex_run_job_use_case",
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
    job = _codex_auth_job()
    jobs = FakeJobRepository(job)
    event_publisher = FakeEventPublisher()
    auth_sessions = FakeAuthSessionRepository()
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        codex_authenticator=FakeCodexAuthenticator(),
        auth_sessions=auth_sessions,
        event_publisher=event_publisher,
    )

    result = await use_case.execute(job)

    assert job.status == JobStatus.RUNNING
    assert isinstance(result, CodexAuthResult)
    assert result.authenticated is True
    assert job.result is None
    assert auth_sessions.session is not None
    assert auth_sessions.session.verification_url == "https://auth.openai.com/device"
    assert auth_sessions.session.user_code == "ABCD-EFGH"
    assert auth_sessions.authenticated_job_id == job.id
    assert all(event.source == "codex_auth_job_use_case" for _, event in jobs.events)
    assert event_publisher.events == jobs.events


async def test_codex_auth_failure_raises_domain_error_and_records_failure() -> None:
    job = _codex_auth_job()
    jobs = FakeJobRepository(job)
    event_publisher = FakeEventPublisher()
    auth_sessions = FakeAuthSessionRepository()
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        codex_authenticator=FakeCodexAuthenticator(
            auth_result=CodexAuthResult(
                authenticated=False,
                error_message="access denied",
            ),
        ),
        auth_sessions=auth_sessions,
        event_publisher=event_publisher,
    )

    with pytest.raises(CodexAuthFailedError, match="access denied"):
        await use_case.execute(job)

    assert auth_sessions.failed == (job.id, "access denied")
    assert jobs.events[-1][1].type == "CodexAuthFailedV1"
    assert event_publisher.events == jobs.events


async def test_codex_auth_cancellation_updates_job_and_kills_authenticator() -> None:
    job = _codex_auth_job()
    jobs = FakeJobRepository(job)
    event_publisher = FakeEventPublisher()
    authenticator = FakeCodexAuthenticator(cancel_on_wait=True)
    auth_sessions = FakeAuthSessionRepository()
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        codex_authenticator=authenticator,
        auth_sessions=auth_sessions,
        event_publisher=event_publisher,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job)

    assert authenticator.cancelled is True
    assert job.status == JobStatus.RUNNING
    assert job.error is None
    assert auth_sessions.cancelled == (job.id, "Job cancelled")
    assert jobs.events[-1][1].type == "CodexAuthCancelledV1"
    assert event_publisher.events == jobs.events


async def test_codex_run_creates_output_and_log_files(tmp_path: Path) -> None:
    job = _codex_run_job(
        CodexRunInputV1(
            prompt="Review repository",
            workdir=str(tmp_path / "workdir"),
        ),
    )
    jobs = FakeJobRepository(job)
    event_publisher = FakeEventPublisher()
    storage = FilesystemFileStorage(root=tmp_path / "files")
    codex_executor = FakeCodexExecutor()
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        storage=storage,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
        event_publisher=event_publisher,
    )

    output = await use_case.execute(job)

    all_files = await jobs.list_files(job.id)
    output_files = await jobs.list_files(job.id, JobFileRole.OUTPUT)
    primary_files = await jobs.list_files(job.id, JobFileRole.PRIMARY_OUTPUT)
    log_files = await jobs.list_files(job.id, JobFileRole.LOG)
    files_by_name = {job_file.name: job_file for job_file in output_files + primary_files}
    assert job.status == JobStatus.RUNNING
    assert output == CodexRunOutput(
        output_file_id=files_by_name["codex_result.txt"].file_id,
        generated_files=1,
        log_files=2,
    )
    assert len(all_files) == 4
    assert len(output_files) == 1
    assert len(primary_files) == 1
    assert len(log_files) == 2
    assert all(job_file.kind in {FileKind.FILE, FileKind.TEXT} for job_file in all_files)
    assert all(job_file.status == FileStatus.ACTIVE for job_file in all_files)
    assert await storage.read(files_by_name["codex_result.txt"].location) == b"Codex result"
    assert await storage.read(files_by_name["changed.py"].location) == b"print('changed')\n"
    assert codex_executor.prompt == "Review repository"
    assert codex_executor.workdir == tmp_path / "workdir" / str(job.id)
    assert [event.type for _, event in jobs.events] == [
        "CodexRunStartedV1",
        "CodexExecOutputV1",
        "CodexRunFileCreatedV1",
        "CodexRunFileCreatedV1",
        "CodexRunFileCreatedV1",
        "CodexRunFileCreatedV1",
        "CodexRunSucceededV1",
    ]
    payload = cast(dict[str, object], jobs.events[1][1].payload)
    assert payload["line"] == '{"type":"message","message":"running"}'
    assert event_publisher.events == jobs.events


async def test_codex_run_cancellation_updates_job_and_kills_executor(
    tmp_path: Path,
) -> None:
    job = _codex_run_job(
        CodexRunInputV1(
            prompt="Review repository",
            workdir=str(tmp_path / "workdir"),
        ),
    )
    jobs = FakeJobRepository(job)
    event_publisher = FakeEventPublisher()
    storage = FilesystemFileStorage(root=tmp_path / "files")
    codex_executor = FakeCodexExecutor(cancel_on_exec=True)
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        storage=storage,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
        event_publisher=event_publisher,
    )

    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job)

    assert codex_executor.cancelled is True
    assert job.status == JobStatus.RUNNING
    assert job.error is None
    assert jobs.events[-1][1].type == "CodexRunCancelledV1"
    assert event_publisher.events == jobs.events
