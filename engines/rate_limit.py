"""In-memory rate limiter (per-user/API-key). Postgres-backed in prod via Supabase."""

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_calls: int = 60, window_s: int = 60):
        self.max_calls = max_calls
        self.window_s = window_s
        self._hits = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        q = self._hits[key]
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.max_calls:
            return False
        q.append(now)
        return True

    def remaining(self, key: str) -> int:
        q = self._hits[key]
        return max(0, self.max_calls - len(q))


GLOBAL_LIMITER = RateLimiter(max_calls=120, window_s=60)
