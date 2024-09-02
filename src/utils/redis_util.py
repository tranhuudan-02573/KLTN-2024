from datetime import timedelta, datetime
from typing import Any, Awaitable

import redis

from src.config.app_config import get_settings

settings = get_settings()
redis_client = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT,
                                 password=settings.REDIS_PASSWORD, db=0,
                                 decode_responses=True)


def is_allowed(key: str, max_calls: int, time_frame: int) -> bool:
    current_time = int(datetime.now().timestamp())
    redis_key = f"rate_limit:{key}"

    # Sử dụng pipeline để thực hiện các lệnh liên tiếp
    pipeline = redis_client.pipeline()
    pipeline.zremrangebyscore(redis_key, 0, current_time - time_frame)
    pipeline.zcard(redis_key)
    pipeline.zadd(redis_key, {str(current_time): current_time})
    pipeline.expire(redis_key, time_frame)
    results = pipeline.execute()

    call_count = results[1]
    return call_count < max_calls


def update(key: str, time_frame: int):
    current_time = int(datetime.now().timestamp())
    redis_key = f"rate_limit:{key}"

    pipeline = redis_client.pipeline()
    pipeline.zadd(redis_key, {str(current_time): current_time})
    pipeline.expire(redis_key, time_frame)
    pipeline.execute()


def reset(key: str):
    redis_key = f"rate_limit:{key}"
    redis_client.delete(redis_key)


def set_user_token_in_redis(user_id: str, token_type: str, token: str, expires_delta: timedelta):
    key = f"user:{user_id}:{token_type}"
    redis_client.set(key, token)
    redis_client.expire(key, int(expires_delta.total_seconds()))


def get_user_token_from_redis(user_id: str, token_type: str) -> tuple[Awaitable, Awaitable | Any] | tuple[None, None]:
    key = f"user:{user_id}:{token_type}"
    token = redis_client.get(key)
    if token:
        remaining_time = redis_client.ttl(key)
        return token, remaining_time
    return None, None


def delete_user_token_from_redis(user_id: str, token_type: str):
    key = f"user:{user_id}:{token_type}"
    redis_client.delete(key)
