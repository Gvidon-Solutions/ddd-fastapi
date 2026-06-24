"""Codex ARQ task tests."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from app.domain.job import (
    Actor,
    ActorType,
    ArtifactRole,
    Job,
    JobArtifact,
    JobArtifactRepository,
    JobEvent,
    JobEventRepository,
    JobRepository,
    JobStatus,
)
from app.domain.job.codex_auth_job_use_case import (
    CodexAuthJobResult,
    CodexAuthResult,
    CodexDeviceAuth,
)
from app.infrastructure.job_artifact_storage import FilesystemJobArtifactStorage
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
        self.jobs = {job.job_id: job}

    async def create(self, job: Job) -> None:
        """Create a job."""
        self.jobs[job.job_id] = job

    async def get(self, job_id: UUID) -> Job:
        """Return a job."""
        return self.jobs[job_id]

    async def save(self, job: Job) -> None:
        """Save a job."""
        self.jobs[job.job_id] = job


class FakeJobArtifactRepository(JobArtifactRepository):
    """Store artifacts in memory."""

    def __init__(self) -> None:
        self.artifacts: list[JobArtifact] = []

    async def create(self, artifact: JobArtifact) -> None:
        """Create an artifact."""
        self.artifacts.append(artifact)

    async def list_by_job(
        self,
        job_id: UUID,
        role: ArtifactRole | None = None,
    ) -> list[JobArtifact]:
        """Return artifacts for a job."""
        artifacts = [artifact for artifact in self.artifacts if artifact.job_id == job_id]
        if role is not None:
            artifacts = [artifact for artifact in artifacts if artifact.role == role]
        return artifacts


class FakeJobEventRepository(JobEventRepository):
    """Store events in memory."""

    def __init__(self) -> None:
        self.events: list[JobEvent] = []

    async def append(self, event: JobEvent) -> None:
        """Append an event."""
        self.events.append(event)

    async def list_by_job(self, job_id: UUID) -> list[JobEvent]:
        """Return events for a job."""
        return [
            event
            for event in self.events
            if event.payload.job_id_issuer == job_id
        ]


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
    job_name: str | None = None,
    job_input: dict | None = None,
) -> Job:
    return Job(
        job_id=uuid4(),
        job_type=job_type,
        job_name=job_name or job_type,
        job_description=None,
        job_input=job_input,
        job_status=JobStatus.QUEUED,
        job_stage=None,
        result_summary=None,
        root_initiator=Actor(type=ActorType.USER, id="anton"),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        updated_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        job_error=None,
    )


async def test_codex_auth_writes_device_login_to_stage() -> None:
    # Arrange
    job = _job("codex_auth")
    jobs = FakeJobRepository(job)
    job_events = FakeJobEventRepository()

    # Act
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=FakeCodexAuthenticator(),
    )
    result = await use_case.execute(job.job_id)

    # Assert
    assert job.job_status == JobStatus.SUCCEEDED
    assert isinstance(result, CodexAuthJobResult)
    assert result.authenticated is True
    assert job.job_stage is not None
    assert job.job_stage.data is not None
    assert job.job_stage.data["verification_url"] == "https://auth.openai.com/device"
    assert job.job_stage.data["device_code"] == "ABCD-EFGH"
    assert job.job_stage.data["status"] == "authenticated"
    assert all(
        event.source == f"codex_auth_job_use_case/{job.job_id}"
        for event in job_events.events
    )


async def test_codex_auth_cancellation_updates_job_and_kills_authenticator() -> None:
    # Arrange
    job = _job("codex_auth")
    jobs = FakeJobRepository(job)
    job_events = FakeJobEventRepository()
    authenticator = FakeCodexAuthenticator(cancel_on_wait=True)
    use_case = new_codex_auth_use_case(
        jobs=jobs,
        job_events=job_events,
        codex_authenticator=authenticator,
    )

    # Act / Assert
    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job.job_id)

    assert authenticator.cancelled is True
    assert job.job_status == JobStatus.CANCELLED
    assert job.job_error is not None
    assert job.job_error.code == "CancelledError"
    assert job.job_stage is not None
    assert job.job_stage.data is not None
    assert job.job_stage.data["status"] == "cancelled"
    assert job_events.events[-1].type == "CodexAuthCancelledV1"


async def test_codex_run_creates_output_and_log_artifacts(tmp_path: Path) -> None:
    # Arrange
    job = _job(
        "codex_run",
        job_input={
            "prompt": "Review repository",
            "workdir": str(tmp_path / "workdir"),
        },
    )
    jobs = FakeJobRepository(job)
    artifacts = FakeJobArtifactRepository()
    storage = FilesystemJobArtifactStorage(root=tmp_path / "artifacts")
    job_events = FakeJobEventRepository()
    codex_executor = FakeCodexExecutor()

    # Act
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        artifacts=artifacts,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
    )
    summary = await use_case.execute(job.job_id)

    # Assert
    all_artifacts = await artifacts.list_by_job(job.job_id)
    output_artifacts = await artifacts.list_by_job(job.job_id, ArtifactRole.OUTPUT)
    log_artifacts = await artifacts.list_by_job(job.job_id, ArtifactRole.LOG)
    output_artifacts_by_name = {artifact.name: artifact for artifact in output_artifacts}
    assert job.job_status == JobStatus.SUCCEEDED
    assert summary["output_artifact_id"] == str(
        output_artifacts_by_name["codex_result.txt"].artifact_id
    )
    assert summary["generated_artifacts"] == 1
    assert summary["log_artifacts"] == 2
    assert len(all_artifacts) == 4
    assert len(output_artifacts) == 2
    assert len(log_artifacts) == 2
    assert (
        await storage.read(output_artifacts_by_name["codex_result.txt"].location)
        == b"Codex result"
    )
    assert (
        await storage.read(output_artifacts_by_name["changed.py"].location)
        == b"print('changed')\n"
    )
    assert codex_executor.prompt == "Review repository"
    assert codex_executor.workdir == tmp_path / "workdir" / str(job.job_id)


async def test_codex_run_cancellation_updates_job_and_kills_executor(
    tmp_path: Path,
) -> None:
    # Arrange
    job = _job(
        "codex_run",
        job_input={
            "prompt": "Review repository",
            "workdir": str(tmp_path / "workdir"),
        },
    )
    jobs = FakeJobRepository(job)
    artifacts = FakeJobArtifactRepository()
    storage = FilesystemJobArtifactStorage(root=tmp_path / "artifacts")
    job_events = FakeJobEventRepository()
    codex_executor = FakeCodexExecutor(cancel_on_exec=True)
    use_case = new_codex_run_job_use_case(
        jobs=jobs,
        artifacts=artifacts,
        storage=storage,
        job_events=job_events,
        codex_executor=codex_executor,
        default_working_directory=tmp_path / "default-workdir",
    )

    # Act / Assert
    with pytest.raises(asyncio.CancelledError):
        await use_case.execute(job.job_id)

    assert codex_executor.cancelled is True
    assert job.job_status == JobStatus.CANCELLED
    assert job.job_error is not None
    assert job.job_error.code == "CancelledError"
    assert job.job_stage is not None
    assert job.job_stage.data is not None
    assert job.job_stage.data["status"] == "cancelled"
    assert job_events.events[-1].type == "CodexRunCancelledV1"
