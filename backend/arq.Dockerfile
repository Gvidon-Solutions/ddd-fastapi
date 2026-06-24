FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    CODEX_JOB_WORKING_DIRECTORY=/opt/backend/app/infrastructure/arq/.codex_work_dir \
    CODEX_WORKSPACE=/opt/backend/app/infrastructure/arq/.codex_work_dir \
    PATH=/root/.local/bin:/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /opt/backend

COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /uvx /usr/local/bin/

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/*

RUN curl -fsSL https://chatgpt.com/codex/install.sh | sh \
    && /root/.local/bin/codex --version \
    && ln -sf /root/.local/bin/codex /usr/local/bin/codex

COPY backend/pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project --project /opt/backend

COPY backend/app/__init__.py backend/app/config.py app/
COPY backend/app/domain/__init__.py app/domain/
COPY backend/app/domain/job app/domain/job
COPY backend/app/usecase/__init__.py app/usecase/
COPY backend/app/usecase/job app/usecase/job
COPY backend/app/infrastructure/__init__.py app/infrastructure/
COPY backend/app/infrastructure/arq/__init__.py backend/app/infrastructure/arq/job_queue.py backend/app/infrastructure/arq/settings.py backend/app/infrastructure/arq/worker.py app/infrastructure/arq/
COPY backend/app/infrastructure/arq/jobs app/infrastructure/arq/jobs
COPY backend/app/infrastructure/arq/.codex_work_dir/.gitkeep app/infrastructure/arq/.codex_work_dir/.gitkeep
COPY backend/app/infrastructure/arq/.codex_work_dir/.codex/config.toml app/infrastructure/arq/.codex_work_dir/.codex/config.toml
COPY backend/app/infrastructure/job_artifact_storage app/infrastructure/job_artifact_storage
COPY backend/app/infrastructure/codex app/infrastructure/codex
COPY backend/app/infrastructure/sqlmodel/__init__.py backend/app/infrastructure/sqlmodel/datetime.py app/infrastructure/sqlmodel/
COPY backend/app/infrastructure/sqlmodel/job app/infrastructure/sqlmodel/job

RUN mkdir -p "${CODEX_WORKSPACE}/.codex"

ENV HOME=/opt/backend/app/infrastructure/arq/.codex_work_dir

WORKDIR /opt/backend

CMD ["arq", "app.infrastructure.arq.worker.WorkerSettings"]
