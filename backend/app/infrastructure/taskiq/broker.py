"""Taskiq Redis broker configuration."""

from taskiq_redis import RedisAsyncResultBackend, RedisStreamBroker

from app.config import settings

result_backend = RedisAsyncResultBackend(
    redis_url=settings.REDIS_URL,
    result_ex_time=settings.TASKIQ_RESULT_TTL_SECONDS,
    prefix_str="skills-dddpy",
)

broker = RedisStreamBroker(
    url=settings.REDIS_URL,
    queue_name=settings.TASKIQ_QUEUE_NAME,
    consumer_group_name=settings.TASKIQ_CONSUMER_GROUP_NAME,
    maxlen=settings.TASKIQ_QUEUE_MAXLEN,
).with_result_backend(result_backend)
