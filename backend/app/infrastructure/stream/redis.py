"""FastStream Redis broker instance."""

from faststream.redis import RedisBroker

from app.config import settings

redis_broker = RedisBroker(settings.REDIS_URL)
