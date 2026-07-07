"""Expose job repository contracts."""

from __future__ import annotations

from .job_repository import JobExecutionRecord, JobRepository

__all__ = (
    "JobExecutionRecord",
    "JobRepository",
)
