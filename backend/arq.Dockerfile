FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    CODEX_JOB_WORKING_DIRECTORY=/opt/backend/app/infrastructure/arq/codex_workspace \
    CODEX_WORKSPACE=/opt/backend/app/infrastructure/arq/codex_workspace \
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
COPY backend/app/domain/codex_job app/domain/codex_job
COPY backend/app/usecase/__init__.py app/usecase/
COPY backend/app/usecase/codex_job app/usecase/codex_job
COPY backend/app/infrastructure/__init__.py app/infrastructure/
COPY backend/app/infrastructure/arq/__init__.py backend/app/infrastructure/arq/codex_job_queue.py backend/app/infrastructure/arq/codex_job_runner.py backend/app/infrastructure/arq/deps.py backend/app/infrastructure/arq/settings.py backend/app/infrastructure/arq/worker.py app/infrastructure/arq/
COPY backend/app/infrastructure/arq/codex_workspace/.gitkeep app/infrastructure/arq/codex_workspace/.gitkeep
COPY backend/app/infrastructure/arq/codex_workspace/.codex/config.toml app/infrastructure/arq/codex_workspace/.codex/config.toml
COPY backend/app/infrastructure/redis app/infrastructure/redis
COPY backend/app/infrastructure/sqlmodel/__init__.py backend/app/infrastructure/sqlmodel/datetime.py app/infrastructure/sqlmodel/
COPY backend/app/infrastructure/sqlmodel/codex_job app/infrastructure/sqlmodel/codex_job

RUN mkdir -p "${CODEX_WORKSPACE}/.codex"

ENV HOME=/opt/backend/app/infrastructure/arq/codex_workspace

WORKDIR /opt/backend

CMD ["arq", "app.infrastructure.arq.worker.WorkerSettings"]
