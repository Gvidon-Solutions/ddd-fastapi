"""Expose job repository contracts."""

from __future__ import annotations

from app.domain.job.base.value_objects.job_execution_record import JobExecutionRecord

from .job_repository import JobRepository

__all__ = (
    "JobExecutionRecord",
    "JobRepository",
)
