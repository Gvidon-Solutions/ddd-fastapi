"""Codex ARQ task tests."""

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
from app.infrastructure.arq.jobs.codex_run import execute_codex_run
from app.infrastructure.artifact_storage import FilesystemArtifactStorage
from app.usecase.codex import (
    CodexAuthenticator,
    new_codex_auth_use_case,
)
from app.usecase.job import Clock

pytestmark = pytest.mark.anyio


class FixedClock(Clock):
    """Return a fixed timestamp."""

    def now(self) -> datetime:
        """Return the fixed timestamp."""
        return datetime(2026, 6, 23, tzinfo=UTC)


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
        return [event for event in self.events if event.job_id == job_id]


class FakeStream:
    """Async stream backed by lines."""

    def __init__(self, lines: list[bytes]):
        self.lines = lines

    async def readline(self) -> bytes:
        """Return the next stream line."""
        if not self.lines:
            return b""
        return self.lines.pop(0)


class FakeStdin:
    """Writable fake process stdin."""

    def __init__(self) -> None:
        self.content = b""

    def write(self, content: bytes) -> None:
        """Write content."""
        self.content += content

    async def drain(self) -> None:
        """Drain content."""

    def close(self) -> None:
        """Close stdin."""

    async def wait_closed(self) -> None:
        """Wait until stdin is closed."""


class FakeProcess:
    """Fake subprocess."""

    def __init__(
        self,
        stdout_lines: list[bytes],
        stderr_lines: list[bytes] | None = None,
        return_code: int = 0,
        on_wait=None,
    ):
        self.stdout = FakeStream(stdout_lines)
        self.stderr = FakeStream(stderr_lines or [])
        self.stdin = FakeStdin()
        self.returncode: int | None = None
        self.return_code = return_code
        self.on_wait = on_wait

    async def wait(self) -> int:
        """Finish the process."""
        if self.on_wait is not None:
            self.on_wait()
        self.returncode = self.return_code
        return self.return_code


class FakeCodexAuthenticator(CodexAuthenticator):
    """Return fixed Codex auth data."""

    async def start_device_auth(self) -> CodexDeviceAuth:
        """Start fake device auth."""
        return CodexDeviceAuth(
            verification_url="https://auth.openai.com/device",
            user_code="ABCD-EFGH",
        )

    async def await_for_user_login(self) -> CodexAuthResult:
        """Wait for fake user login."""
        return CodexAuthResult(authenticated=True)


def _job(
    name: str,
    input: dict | None = None,
) -> Job:
    return Job(
        id=uuid4(),
        name=name,
        input=input,
        status=JobStatus.QUEUED,
        stage=None,
        result_summary=None,
        root_initiator=Actor(type=ActorType.USER, id="anton"),
        parent_job_id=None,
        requested_at=datetime(2026, 6, 23, tzinfo=UTC),
        started_at=None,
        finished_at=None,
        error=None,
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
    result = await use_case.execute(job.id)

    # Assert
    assert job.status == JobStatus.SUCCEEDED
    assert isinstance(result, CodexAuthJobResult)
    assert result.authenticated is True
    assert job.stage is not None
    assert job.stage.data is not None
    assert job.stage.data["verification_url"] == "https://auth.openai.com/device"
    assert job.stage.data["user_code"] == "ABCD-EFGH"
    assert job.stage.data["device_code"] == "ABCD-EFGH"
    assert job.stage.data["status"] == "authenticated"


async def test_codex_run_creates_output_and_log_artifacts(tmp_path: Path) -> None:
    # Arrange
    job = _job(
        "codex_run",
        input={
            "prompt": "Review repository",
            "workdir": str(tmp_path / "workdir"),
        },
    )
    jobs = FakeJobRepository(job)
    artifacts = FakeJobArtifactRepository()
    storage = FilesystemArtifactStorage(root=tmp_path / "artifacts")
    job_events = FakeJobEventRepository()
    clock = FixedClock()

    async def process_factory(*args, **_kwargs):
        output_path = Path(args[args.index("-o") + 1])

        def write_output() -> None:
            output_path.write_text("Codex result", encoding="utf-8")

        return FakeProcess(
            stdout_lines=[b'{"type":"message","message":"running"}\n'],
            stderr_lines=[b"warning\n"],
            on_wait=write_output,
        )

    # Act
    summary = await execute_codex_run(
        job_id=job.id,
        jobs=jobs,
        artifacts=artifacts,
        storage=storage,
        job_events=job_events,
        clock=clock,
        process_factory=process_factory,
    )

    # Assert
    all_artifacts = await artifacts.list_by_job(job.id)
    output_artifacts = await artifacts.list_by_job(job.id, ArtifactRole.OUTPUT)
    log_artifacts = await artifacts.list_by_job(job.id, ArtifactRole.LOG)
    assert job.status == JobStatus.SUCCEEDED
    assert summary["output_artifact_id"] == str(output_artifacts[0].id)
    assert len(all_artifacts) == 3
    assert len(output_artifacts) == 1
    assert len(log_artifacts) == 2
    assert await storage.read(output_artifacts[0].location) == b"Codex result"
