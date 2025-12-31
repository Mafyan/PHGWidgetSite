from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_seconds: int


class SlidingWindowRateLimiter:
    """
    Простой in-memory rate limit на процесс.
    Для продакшена лучше Redis/nginx, но для MVP виджета достаточно.
    """

    def __init__(self, limit: int, window_seconds: int) -> None:
        self.limit = max(1, int(limit))
        self.window_seconds = max(1, int(window_seconds))
        self._buckets: dict[str, list[float]] = {}

    def check(self, key: str) -> RateLimitResult:
        now = time.time()
        window_start = now - self.window_seconds
        bucket = self._buckets.get(key, [])
        bucket = [t for t in bucket if t >= window_start]

        if len(bucket) >= self.limit:
            oldest = min(bucket) if bucket else now
            reset = int(max(0, (oldest + self.window_seconds) - now))
            self._buckets[key] = bucket
            return RateLimitResult(allowed=False, remaining=0, reset_seconds=reset)

        bucket.append(now)
        self._buckets[key] = bucket
        remaining = max(0, self.limit - len(bucket))
        return RateLimitResult(allowed=True, remaining=remaining, reset_seconds=self.window_seconds)


