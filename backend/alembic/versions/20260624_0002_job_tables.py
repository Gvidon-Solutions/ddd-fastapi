"""Add generic job tables.

Revision ID: 20260624_0002
Revises: 20260622_0001
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260624_0002"
down_revision = "20260622_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create generic job, artifact, event, and dispatch outbox tables."""
    op.create_table(
        "job",
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("input", sa.JSON(), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("initiator", sa.JSON(), nullable=False),
        sa.Column("parent_job_id", sa.Uuid(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["parent_job_id"], ["job.job_id"]),
        sa.PrimaryKeyConstraint("job_id"),
    )
    op.create_index("ix_job_name", "job", ["name"])
    op.create_index("ix_job_status", "job", ["status"])
    op.create_index("ix_job_type", "job", ["type"])
    op.create_index("ix_job_version", "job", ["version"])

    op.create_table(
        "job_dispatch_outbox",
        sa.Column("outbox_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["job.job_id"]),
        sa.PrimaryKeyConstraint("outbox_id"),
    )
    op.create_index("ix_job_dispatch_outbox_job_id", "job_dispatch_outbox", ["job_id"])
    op.create_index(
        "ix_job_dispatch_outbox_status",
        "job_dispatch_outbox",
        ["status"],
    )

    op.create_table(
        "event",
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(length=255), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("job_id_issuer", sa.Uuid(), nullable=True),
        sa.Column("job_event_type", sa.String(length=64), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id_issuer"], ["job.job_id"]),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_event_job_event_type", "event", ["job_event_type"])
    op.create_index("ix_event_job_id_issuer", "event", ["job_id_issuer"])
    op.create_index("ix_event_source", "event", ["source"])
    op.create_index("ix_event_type", "event", ["type"])

    op.create_table(
        "job_artifact",
        sa.Column("artifact_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("location", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_id"], ["job.job_id"]),
        sa.PrimaryKeyConstraint("artifact_id"),
    )
    op.create_index("ix_job_artifact_job_id", "job_artifact", ["job_id"])
    op.create_index("ix_job_artifact_role", "job_artifact", ["role"])


def downgrade() -> None:
    """Drop generic job, artifact, and event tables."""
    op.drop_index("ix_job_artifact_role", table_name="job_artifact")
    op.drop_index("ix_job_artifact_job_id", table_name="job_artifact")
    op.drop_table("job_artifact")

    op.drop_index("ix_event_type", table_name="event")
    op.drop_index("ix_event_source", table_name="event")
    op.drop_index("ix_event_job_id_issuer", table_name="event")
    op.drop_index("ix_event_job_event_type", table_name="event")
    op.drop_table("event")

    op.drop_index("ix_job_dispatch_outbox_status", table_name="job_dispatch_outbox")
    op.drop_index("ix_job_dispatch_outbox_job_id", table_name="job_dispatch_outbox")
    op.drop_table("job_dispatch_outbox")

    op.drop_index("ix_job_version", table_name="job")
    op.drop_index("ix_job_type", table_name="job")
    op.drop_index("ix_job_status", table_name="job")
    op.drop_index("ix_job_name", table_name="job")
    op.drop_table("job")
