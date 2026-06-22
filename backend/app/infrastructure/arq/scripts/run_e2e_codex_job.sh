#!/usr/bin/env bash
set -euo pipefail

PROMPT="${1:-Inspect the workspace and respond with exactly: codex-worker-e2e-ok. Do not modify files.}"
TIMEOUT_SECONDS="${E2E_TIMEOUT_SECONDS:-300}"
COMPOSE="${COMPOSE:-docker compose}"
ARQ_IMAGE="${ARQ_IMAGE:-skills-dddpy-arq:local}"
CODEX_AUTH_DIR="backend/app/infrastructure/arq/codex_workspace/.codex"

mkdir -p "${CODEX_AUTH_DIR}"

if ! find "${CODEX_AUTH_DIR}" -mindepth 1 -maxdepth 1 -print -quit | grep -q .; then
  echo "warning: ${CODEX_AUTH_DIR} is empty; Codex is expected to fail without mounted auth/config files" >&2
fi

docker build -t "${ARQ_IMAGE}" -f backend/arq.Dockerfile .
${COMPOSE} up -d db redis

${COMPOSE} run --rm arq python - <<'PY'
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel

from app.config import settings
from app.infrastructure.sqlmodel.codex_job import CodexJobDTO


async def main() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    for attempt in range(30):
        try:
            async with engine.begin() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)
            await engine.dispose()
            return
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(1)


asyncio.run(main())
PY

${COMPOSE} stop arq >/dev/null 2>&1 || true

JOB_ID="$(
  ${COMPOSE} run --rm arq python - "${PROMPT}" <<'PY'
import asyncio
import sys
from uuid import UUID

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.codex_job.entities import CodexJob
from app.domain.codex_job.value_objects import CodexJobPrompt
from app.infrastructure.arq import new_codex_job_starter
from app.infrastructure.sqlmodel.codex_job import new_codex_job_repository


async def main() -> None:
    prompt = sys.argv[1]
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async with AsyncSession(engine) as session:
        repository = new_codex_job_repository(session)
        codex_job = CodexJob.create(CodexJobPrompt(prompt))
        await repository.save(codex_job)
        await session.commit()

        backend_job_id = await new_codex_job_starter().start(codex_job.id)
        codex_job.attach_backend_job(backend_job_id)
        await repository.save(codex_job)
        await session.commit()
        print(codex_job.id.value)
    await engine.dispose()


asyncio.run(main())
PY
)"

echo "enqueued codex_job_id=${JOB_ID}"

${COMPOSE} up -d arq

${COMPOSE} run --rm arq python - "${JOB_ID}" "${TIMEOUT_SECONDS}" <<'PY'
import asyncio
import sys

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.domain.codex_job.value_objects import CodexJobId, CodexJobStatus
from app.infrastructure.sqlmodel.codex_job import new_codex_job_repository


async def main() -> None:
    codex_job_id = CodexJobId(UUID(sys.argv[1]))
    timeout_seconds = int(sys.argv[2])
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    terminal_statuses = {
        CodexJobStatus.SUCCEEDED,
        CodexJobStatus.FAILED,
        CodexJobStatus.ABORTED,
    }

    for _ in range(timeout_seconds):
        async with AsyncSession(engine) as session:
            codex_job = await new_codex_job_repository(session).find_by_id(codex_job_id)
        if codex_job is None:
            print("codex job is missing")
            await engine.dispose()
            raise SystemExit(1)
        if codex_job.status in terminal_statuses:
            print(f"status={codex_job.status.value}")
            if codex_job.result:
                print(f"result={codex_job.result}")
            if codex_job.error_message:
                print(f"error={codex_job.error_message}")
            await engine.dispose()
            raise SystemExit(0 if codex_job.status == CodexJobStatus.SUCCEEDED else 1)
        await asyncio.sleep(1)

    print(f"timeout waiting for codex job {codex_job_id.value}")
    await engine.dispose()
    raise SystemExit(1)


asyncio.run(main())
PY
