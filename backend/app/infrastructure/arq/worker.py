"""ARQ worker configuration."""

from app.config import settings
from app.infrastructure.arq.jobs import codex_auth, codex_run
from app.infrastructure.arq.settings import arq_redis_settings


class WorkerSettings:
    """Configure the ARQ worker process."""

    functions = [codex_auth, codex_run]
    redis_settings = arq_redis_settings()
    queue_name = settings.ARQ_QUEUE_NAME
    job_timeout = settings.ARQ_JOB_TIMEOUT_SECONDS
    keep_result = settings.ARQ_RESULT_TTL_SECONDS
    allow_abort_jobs = True
