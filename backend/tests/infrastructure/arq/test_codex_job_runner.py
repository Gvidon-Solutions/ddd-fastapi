"""Codex job runner tests."""

from pathlib import Path

from pydantic import BaseModel

from app.domain.codex_job.value_objects import CodexJobId, CodexJobPrompt
from app.infrastructure.arq.codex_job_runner import (
    CodexCliJobRunner,
    _codex_exec_args,
    _event_payload,
    _event_type,
)


class FakePydanticEvent(BaseModel):
    """Fake OpenAI Agents stream event."""

    type: str
    text: str


class FakeEventPublisher:
    """Fake Codex job event publisher."""

    async def publish(
        self,
        codex_job_id: CodexJobId,
        event_type: str,
        payload: str,
    ) -> None:
        """Ignore published events."""


def test_event_type_uses_event_type_field() -> None:
    # Arrange
    event = FakePydanticEvent(type="run_item_stream_event", text="hello")

    # Act
    event_type = _event_type(event)

    # Assert
    assert event_type == "run_item_stream_event"


def test_event_payload_serializes_pydantic_event() -> None:
    # Arrange
    event = FakePydanticEvent(type="raw_response_event", text="hello")

    # Act
    payload = _event_payload(event)

    # Assert
    assert payload == '{"type":"raw_response_event","text":"hello"}'


def test_event_payload_serializes_value_objects() -> None:
    # Arrange
    event = {"prompt": CodexJobPrompt("Review repository")}

    # Act
    payload = _event_payload(event)

    # Assert
    assert payload == '{"prompt": "Review repository"}'


def test_codex_exec_args_uses_job_workspace(
    monkeypatch,
) -> None:
    # Arrange
    job_workspace = Path("/tmp/codex-home/job-id")
    output_path = job_workspace / ".codex-output.txt"
    monkeypatch.setattr(
        "app.infrastructure.arq.codex_job_runner.settings.CODEX_CLI_PATH",
        "codex",
    )
    monkeypatch.setattr(
        "app.infrastructure.arq.codex_job_runner.settings.CODEX_JOB_MODEL",
        "gpt-5.5",
    )
    monkeypatch.setattr(
        "app.infrastructure.arq.codex_job_runner.settings.CODEX_JOB_SANDBOX_MODE",
        "danger-full-access",
    )
    monkeypatch.setattr(
        "app.infrastructure.arq.codex_job_runner.settings.CODEX_JOB_REASONING_EFFORT",
        "low",
    )
    monkeypatch.setattr(
        "app.infrastructure.arq.codex_job_runner.settings.CODEX_JOB_APPROVAL_POLICY",
        "never",
    )

    # Act
    args = _codex_exec_args(job_workspace=job_workspace, output_path=output_path)

    # Assert
    assert args[args.index("-C") + 1] == str(job_workspace)
    assert args[args.index("-o") + 1] == str(output_path)


def test_process_env_uses_codex_home() -> None:
    # Arrange
    runner = CodexCliJobRunner(event_publisher=FakeEventPublisher())
    codex_home = Path("/tmp/codex-home")

    # Act
    env = runner._process_env(codex_home)

    # Assert
    assert env["HOME"] == str(codex_home)
