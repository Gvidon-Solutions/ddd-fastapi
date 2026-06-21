"""AgentRun SQLModel DTO."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime
from sqlmodel import Field, SQLModel

from app.domain.agent.entities import AgentRun
from app.domain.agent.value_objects import (
    AgentPrompt,
    AgentRunId,
    AgentRunStatus,
    AgentWorkflowName,
)
from app.domain.user.value_objects import UserId
from app.infrastructure.sqlmodel.datetime import get_datetime_utc


class AgentRunDTO(SQLModel, table=True):
    """Persisted agent run record."""

    __tablename__ = "agent_run"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    workflow_name: str = Field(max_length=120, index=True)
    input_prompt: str
    status: str = Field(max_length=32, index=True)
    created_by_user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
        ondelete="SET NULL",
    )
    result: str | None = None
    error_message: str | None = None
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    started_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )
    finished_at: datetime | None = Field(
        default=None,
        sa_column=Column(DateTime(timezone=True), nullable=True),
    )

    def to_entity(self) -> AgentRun:
        """Convert this persistence DTO to a domain entity."""
        return AgentRun(
            id=AgentRunId(self.id),
            workflow_name=AgentWorkflowName(self.workflow_name),
            input_prompt=AgentPrompt(self.input_prompt),
            status=AgentRunStatus(self.status),
            created_by_user_id=UserId(self.created_by_user_id)
            if self.created_by_user_id
            else None,
            result=self.result,
            error_message=self.error_message,
            created_at=self.created_at or get_datetime_utc(),
            started_at=self.started_at,
            finished_at=self.finished_at,
        )

    @staticmethod
    def from_entity(agent_run: AgentRun) -> "AgentRunDTO":
        """Build a persistence DTO from a domain entity."""
        return AgentRunDTO(
            id=agent_run.id.value,
            workflow_name=agent_run.workflow_name.value,
            input_prompt=agent_run.input_prompt.value,
            status=agent_run.status.value,
            created_by_user_id=agent_run.created_by_user_id.value
            if agent_run.created_by_user_id
            else None,
            result=agent_run.result,
            error_message=agent_run.error_message,
            created_at=agent_run.created_at,
            started_at=agent_run.started_at,
            finished_at=agent_run.finished_at,
        )
