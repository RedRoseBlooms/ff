"""Rate limiting and anti-spam utilities."""

from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque


class RateLimiter:
    """Sliding window rate limiter per key."""

    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = asyncio.Lock()

    async def acquire(self, key: str) -> bool:
        async with self._lock:
            now = time.monotonic()
            q = self._events[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.max_calls:
                return False
            q.append(now)
            return True


class InteractionLock:
    """Prevent duplicate interaction processing."""

    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = asyncio.Lock()

    async def try_acquire(self, interaction_id: str) -> bool:
        async with self._lock:
            if interaction_id in self._active:
                return False
            self._active.add(interaction_id)
            return True

    async def release(self, interaction_id: str) -> None:
        async with self._lock:
            self._active.discard(interaction_id)
