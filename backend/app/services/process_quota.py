"""Per-user POST /process quota: Redis sliding window when available, else in-process."""
from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict

from fastapi import HTTPException

from app.config import settings

_lock = threading.Lock()
_calls: dict[str, list[float]] = defaultdict(list)

WINDOW_SECONDS = 3600.0
_REDIS_KEY_PREFIX = "inboxpilot:process_quota:"
_redis_cached: object | None = None  # None = not tried, False = skip Redis, else Redis client


def _redis_client():
    global _redis_cached
    if _redis_cached is False:
        return None
    if _redis_cached is not None:
        return _redis_cached
    try:
        import redis as redis_lib

        c = redis_lib.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1.0,
        )
        c.ping()
        _redis_cached = c
        return c
    except Exception:
        _redis_cached = False
        return None


def _enforce_memory(user_id: str, limit_per_hour: int) -> None:
    now = time.monotonic()
    with _lock:
        bucket = _calls[user_id]
        cutoff = now - WINDOW_SECONDS
        bucket[:] = [t for t in bucket if t > cutoff]
        if len(bucket) >= limit_per_hour:
            raise HTTPException(
                status_code=429,
                detail="Workflow quota exceeded for this account; try again later.",
            )
        bucket.append(now)


def _enforce_redis(user_id: str, limit_per_hour: int) -> None:
    r = _redis_client()
    if r is None:
        _enforce_memory(user_id, limit_per_hour)
        return
    now = time.time()
    key = f"{_REDIS_KEY_PREFIX}{user_id}"
    window_start = now - WINDOW_SECONDS
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zcard(key)
    _, count = pipe.execute()
    if count >= limit_per_hour:
        raise HTTPException(
            status_code=429,
            detail="Workflow quota exceeded for this account; try again later.",
        )
    member = f"{now:.9f}:{uuid.uuid4().hex}"
    r.zadd(key, {member: now})
    r.expire(key, int(WINDOW_SECONDS) + 120)


def enforce_process_quota(user_id: str, limit_per_hour: int) -> None:
    """
    Raise 429 if this user_id has reached limit_per_hour calls in the last hour.
    Uses Redis when reachable (shared across workers); otherwise in-process dict.
    """
    if limit_per_hour <= 0:
        return
    _enforce_redis(user_id, limit_per_hour)
