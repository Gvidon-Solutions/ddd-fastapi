"""Codex workflow runner implemented with the OpenAI Agents SDK."""

from typing import Any

from agents import Agent, Runner
from agents.extensions.experimental.codex import ThreadOptions, TurnOptions, codex_tool

from app.config import settings
from app.domain.agent.entities import AgentRun, AgentRunEvent
from app.domain.agent.value_objects import AgentEventPayload, AgentEventType
from app.usecase.agent import AgentWorkflowRunner, EmitAgentRunEvent

CODEX_DISABLED_MESSAGE = (
    "Codex workflow is disabled. Set CODEX_WORKFLOW_ENABLED=True after "
    "authenticating Codex CLI."
)


def _json_safe(value: Any) -> Any:
    """Convert SDK event payloads into JSON-serializable values."""
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if hasattr(value, "as_dict"):
        return _json_safe(value.as_dict())
    return str(value)


class DisabledCodexWorkflowRunner(AgentWorkflowRunner):
    """Return a clear result when Codex execution is not enabled."""

    async def execute(
        self,
        agent_run: AgentRun,
        emit_event: EmitAgentRunEvent,
    ) -> str:
        """Emit a step event and return the disabled message."""
        await emit_event(
            AgentRunEvent.create(
                run_id=agent_run.id,
                event_type=AgentEventType.STEP,
                payload=AgentEventPayload({"message": CODEX_DISABLED_MESSAGE}),
            )
        )
        return CODEX_DISABLED_MESSAGE


class CodexWorkflowRunner(AgentWorkflowRunner):
    """Execute a workspace-scoped Codex task through the OpenAI Agents SDK."""

    async def execute(
        self,
        agent_run: AgentRun,
        emit_event: EmitAgentRunEvent,
    ) -> str:
        """Run Codex and stream progress into agent run events."""

        async def on_codex_stream(payload: Any) -> None:
            sdk_event = _json_safe(getattr(payload, "event", payload))
            event_type = (
                AgentEventType.TOOL_CALL
                if str(sdk_event.get("type", "")).startswith("item.")
                else AgentEventType.STEP
            )
            await emit_event(
                AgentRunEvent.create(
                    run_id=agent_run.id,
                    event_type=event_type,
                    payload=AgentEventPayload(
                        {
                            "source": "codex_tool",
                            "event": sdk_event,
                        }
                    ),
                )
            )

        agent = Agent(
            name="Codex Workflow",
            instructions=(
                "Use the codex tool for workspace-scoped codebase tasks. "
                "Keep the task bounded to the user's prompt and report the final result."
            ),
            model=settings.CODEX_WORKFLOW_MODEL,
            tools=[
                codex_tool(
                    sandbox_mode=settings.CODEX_WORKFLOW_SANDBOX_MODE,
                    working_directory=settings.CODEX_WORKFLOW_WORKING_DIRECTORY,
                    default_thread_options=ThreadOptions(
                        model=settings.CODEX_WORKFLOW_MODEL,
                        model_reasoning_effort=settings.CODEX_WORKFLOW_REASONING_EFFORT,
                        approval_policy=settings.CODEX_WORKFLOW_APPROVAL_POLICY,
                    ),
                    default_turn_options=TurnOptions(
                        idle_timeout_seconds=(
                            settings.CODEX_WORKFLOW_IDLE_TIMEOUT_SECONDS
                        ),
                    ),
                    persist_session=True,
                    on_stream=on_codex_stream,
                )
            ],
        )
        result = Runner.run_streamed(
            agent,
            input=agent_run.input_prompt.value,
            max_turns=settings.AGENT_WORKFLOW_MAX_TURNS,
        )
        async for event in result.stream_events():
            if event.type == "agent_updated_stream_event":
                await emit_event(
                    AgentRunEvent.create(
                        run_id=agent_run.id,
                        event_type=AgentEventType.STEP,
                        payload=AgentEventPayload(
                            {
                                "source": "agents_sdk",
                                "agent": event.new_agent.name,
                            }
                        ),
                    )
                )

        return str(result.final_output)
