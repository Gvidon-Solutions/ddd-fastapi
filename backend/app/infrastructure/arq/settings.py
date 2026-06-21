"""ARQ Redis settings helpers."""

from urllib.parse import unquote, urlparse

from arq.connections import RedisSettings

from app.config import settings


def arq_redis_settings() -> RedisSettings:
    """Build ARQ Redis settings from the configured Redis URL."""
    parsed = urlparse(settings.REDIS_URL)

    database = int(parsed.path.removeprefix("/") or "0")
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        username=unquote(parsed.username) if parsed.username else None,
        password=unquote(parsed.password) if parsed.password else None,
        ssl=parsed.scheme == "rediss",
    )
