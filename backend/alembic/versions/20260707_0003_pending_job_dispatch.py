"""Replace job dispatch outbox with pending job dispatch state.

Revision ID: 20260707_0003
Revises: 20260624_0002
Create Date: 2026-07-07
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260707_0003"
down_revision = "20260624_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Move dispatch retry state onto the job table and drop the outbox."""
    op.add_column(
        "job",
        sa.Column(
            "dispatch_attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "job",
        sa.Column("next_dispatch_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("job", sa.Column("last_dispatch_error", sa.String(), nullable=True))
    op.add_column(
        "job",
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.execute(
        """
        update job
        set
            status = 'pending',
            dispatch_attempts = job_dispatch_outbox.attempts,
            next_dispatch_at = job_dispatch_outbox.next_attempt_at,
            last_dispatch_error = job_dispatch_outbox.last_error,
            dispatched_at = job_dispatch_outbox.dispatched_at,
            updated_at = job_dispatch_outbox.updated_at
        from job_dispatch_outbox
        where job.job_id = job_dispatch_outbox.job_id
            and job_dispatch_outbox.status = 'pending'
            and job.status = 'queued'
        """
    )
    op.execute(
        """
        update job
        set dispatched_at = job_dispatch_outbox.dispatched_at
        from job_dispatch_outbox
        where job.job_id = job_dispatch_outbox.job_id
            and job_dispatch_outbox.status = 'dispatched'
            and job_dispatch_outbox.dispatched_at is not null
        """
    )

    op.drop_index("ix_job_dispatch_outbox_status", table_name="job_dispatch_outbox")
    op.drop_index("ix_job_dispatch_outbox_job_id", table_name="job_dispatch_outbox")
    op.drop_table("job_dispatch_outbox")


def downgrade() -> None:
    """Restore the outbox table shape and remove job dispatch columns."""
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

    op.drop_column("job", "dispatched_at")
    op.drop_column("job", "last_dispatch_error")
    op.drop_column("job", "next_dispatch_at")
    op.drop_column("job", "dispatch_attempts")
