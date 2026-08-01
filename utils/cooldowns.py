"""In-memory cooldown tracking with optional DB persistence."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable


@dataclass(slots=True)
class CooldownResult:
    on_cooldown: bool
    remaining: float


class CooldownManager:
    """Thread-safe-ish async cooldown manager."""

    def __init__(self) -> None:
        self._store: dict[str, float] = {}

    def key(self, user_id: int, command: str) -> str:
        return f"{user_id}:{command}"

    def check(self, user_id: int, command: str, duration: float) -> CooldownResult:
        k = self.key(user_id, command)
        now = time.monotonic()
        expires = self._store.get(k, 0.0)
        if expires > now:
            return CooldownResult(True, expires - now)
        return CooldownResult(False, 0.0)

    def set(self, user_id: int, command: str, duration: float) -> None:
        self._store[self.key(user_id, command)] = time.monotonic() + duration

    def remaining_human(self, seconds: float) -> str:
        if seconds >= 3600:
            h = int(seconds // 3600)
            m = int((seconds % 3600) // 60)
            return f"{h}h {m}m"
        if seconds >= 60:
            m = int(seconds // 60)
            s = int(seconds % 60)
            return f"{m}m {s}s"
        return f"{int(seconds)}s"


def discord_timestamp_relative(unix: int) -> str:
    return f"<t:{unix}:R>"
