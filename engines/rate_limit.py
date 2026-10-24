"""Distributed-capable rate limiter (per-user/API-key).

Default backend is an in-process sliding window (single replica).
When REDIS_URL is set, a Redis-backed sliding window is used so
multi-replica deployments share one budget. Falls back to in-memory
if Redis is unreachable (fail-open on infra outage, still enforce
per-replica limits).

API:
    RateLimiter(max_calls, window_s)  — same interface as before.
    GLOBAL_LIMITER                     — process-wide default budget.
    get_limiter(name, max_calls, window_s) — named limiter registry.
"""

import os
import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding-window limiter. Redis-backed when REDIS_URL is configured."""

    def __init__(self, max_calls: int = 60, window_s: int = 60, name: str = "default"):
        self.max_calls = max_calls
        self.window_s = window_s
        self.name = name
        self._hits: dict[str, deque] = defaultdict(deque)
        self._redis = None
        self._redis_failed = False
        redis_url = os.environ.get("REDIS_URL", "").strip()
        if redis_url:
            self._redis = self._try_connect(redis_url)

    @staticmethod
    def _try_connect(redis_url: str):
        try:
            import redis  # type: ignore

            client = redis.Redis.from_url(redis_url, decode_responses=True, socket_timeout=1.0)
            client.ping()
            return client
        except Exception:
            return None

    def _redis_allow(self, key: str) -> bool | None:
        if self._redis is None or self._redis_failed:
            return None
        try:
            rkey = f"rl:{self.name}:{key}"
            now = time.time()
            pipe = self._redis.pipeline()
            pipe.zremrangebyscore(rkey, 0, now - self.window_s)
            pipe.zadd(rkey, {f"{now}:{id(object())}": now})
            pipe.zcard(rkey)
            pipe.expire(rkey, self.window_s + 5)
            _, _, count, _ = pipe.execute()
            return int(count) <= self.max_calls
        except Exception:
            self._redis_failed = True
            return None

    def allow(self, key: str) -> bool:
        result = self._redis_allow(key)
        if result is not None:
            return result
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True

    def remaining(self, key: str) -> int:
        if self._redis is not None and not self._redis_failed:
            try:
                rkey = f"rl:{self.name}:{key}"
                return max(0, self.max_calls - int(self._redis.zcard(rkey)))
            except Exception:
                pass
        q = self._hits[key]
        return max(0, self.max_calls - len(q))


GLOBAL_LIMITER = RateLimiter(max_calls=120, window_s=60, name="api-global")

_limiters: dict[str, RateLimiter] = {"api-global": GLOBAL_LIMITER}


def get_limiter(name: str, max_calls: int = 60, window_s: int = 60) -> RateLimiter:
    """Return a named limiter (created on first use)."""
    if name not in _limiters:
        _limiters[name] = RateLimiter(max_calls=max_calls, window_s=window_s, name=name)
    return _limiters[name]
