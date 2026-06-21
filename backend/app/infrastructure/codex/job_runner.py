"""Codex job runner implementation."""

import json
from dataclasses import asdict, is_dataclass
from typing import Any

from app.config import settings
from app.domain.codex_job.entities import CodexJob
from app.infrastructure.redis import new_codex_job_event_publisher
from app.usecase.codex_job import CodexJobEventPublisher, CodexJobRunner


def _event_type(event: Any) -> str:
    """Return a stable event type string."""
    event_type = getattr(event, "type", None)
    if isinstance(event_type, str) and event_type:
        return event_type
    return type(event).__name__


def _event_payload(event: Any) -> str:
    """Serialize one Codex stream event."""
    model_dump_json = getattr(event, "model_dump_json", None)
    if callable(model_dump_json):
        return str(model_dump_json())

    model_dump = getattr(event, "model_dump", None)
    if callable(model_dump):
        return json.dumps(model_dump(mode="json"), default=str)

    return json.dumps(event, default=_json_default)


def _json_default(value: Any) -> Any:
    """Serialize non-standard event payload values."""
    if is_dataclass(value):
        object_value = getattr(value, "value", None)
        if isinstance(object_value, str | int | float | bool | None):
            return object_value
        return asdict(value)
    return str(value)


class CodexCliJobRunner(CodexJobRunner):
    """Execute Codex jobs."""

    def __init__(self, event_publisher: CodexJobEventPublisher):
        """Store runner dependencies."""
        self.event_publisher = event_publisher

    async def execute(self, codex_job: CodexJob) -> str:
        """Run a Codex job and return its result."""
        from agents import Agent, Runner
        from agents.extensions.experimental.codex import (
            ThreadOptions,
            TurnOptions,
            codex_tool,
        )

        agent = Agent(
            name="Codex Job",
            instructions=(
                "Use the codex tool for workspace-scoped codebase tasks. "
                "Keep the task bounded to the user's prompt and report the final result."
            ),
            model=settings.CODEX_JOB_MODEL,
            tools=[
                codex_tool(
                    sandbox_mode=settings.CODEX_JOB_SANDBOX_MODE,
                    working_directory=settings.CODEX_JOB_WORKING_DIRECTORY,
                    default_thread_options=ThreadOptions(
                        model=settings.CODEX_JOB_MODEL,
                        model_reasoning_effort=settings.CODEX_JOB_REASONING_EFFORT,
                        approval_policy=settings.CODEX_JOB_APPROVAL_POLICY,
                    ),
                    default_turn_options=TurnOptions(
                        idle_timeout_seconds=settings.CODEX_JOB_IDLE_TIMEOUT_SECONDS,
                    ),
                    persist_session=True,
                )
            ],
        )
        result = Runner.run_streamed(
            agent,
            input=codex_job.prompt.value,
            max_turns=settings.CODEX_JOB_MAX_TURNS,
        )
        async for event in result.stream_events():
            await self.event_publisher.publish(
                codex_job_id=codex_job.id,
                event_type=_event_type(event),
                payload=_event_payload(event),
            )
        return str(result.final_output)


def new_codex_job_runner(
    event_publisher: CodexJobEventPublisher | None = None,
) -> CodexJobRunner:
    """Create a Codex job runner."""
    return CodexCliJobRunner(event_publisher or new_codex_job_event_publisher())
