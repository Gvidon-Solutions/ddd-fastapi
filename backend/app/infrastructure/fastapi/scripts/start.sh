#!/usr/bin/env sh
set -eu

set +e
python - <<'PY'
import asyncio

from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings


async def main() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    async with engine.connect() as connection:
        tables = set(await connection.run_sync(lambda conn: inspect(conn).get_table_names()))
    await engine.dispose()

    app_tables = {"codex_job", "item", "user"}
    if "alembic_version" not in tables and app_tables.issubset(tables):
        raise SystemExit(42)


asyncio.run(main())
PY
stamp_status="$?"
set -e

if [ "${stamp_status}" -eq 42 ]; then
  alembic stamp head
elif [ "${stamp_status}" -ne 0 ]; then
  exit "${stamp_status}"
fi

alembic upgrade head

python - <<'PY'
import asyncio

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession

from app.config import settings
from app.infrastructure.sqlmodel import database


async def main() -> None:
    engine = create_async_engine(str(settings.SQLALCHEMY_DATABASE_URI))
    for attempt in range(30):
        try:
            async with AsyncSession(engine) as session:
                await database.init_db(session)
                await session.commit()
            await engine.dispose()
            return
        except Exception:
            if attempt == 29:
                raise
            await asyncio.sleep(1)


asyncio.run(main())
PY

exec fastapi run app/main.py --host 0.0.0.0 --port 8000
