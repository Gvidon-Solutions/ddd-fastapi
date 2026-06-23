FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local \
    PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

WORKDIR /opt/backend

COPY --from=ghcr.io/astral-sh/uv:0.9.16 /uv /uvx /usr/local/bin/

COPY backend/pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project --project /opt/backend

COPY backend/app app
COPY backend/alembic alembic
COPY backend/alembic.ini alembic.ini
COPY backend/app/infrastructure/fastapi/scripts/start.sh scripts/start.sh

RUN chmod +x scripts/start.sh

CMD ["scripts/start.sh"]
