"""Automatic server events."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from utils.logging import get_logger

logger = get_logger(__name__)

EVENT_TYPES = ["rain", "jackpot", "flash_giveaway", "double_xp", "double_money"]


class EventService:
    def __init__(self, db) -> None:
        self.db = db

    async def get_active_multipliers(self, guild_id: int) -> dict[str, Decimal]:
        rows = await self.db.fetch(
            """
            SELECT event_type, multiplier FROM active_events
            WHERE guild_id = $1 AND ends_at > NOW()
            """,
            guild_id,
        )
        return {r["event_type"]: Decimal(str(r["multiplier"])) for r in rows}

    async def start_event(
        self,
        guild_id: int,
        event_type: str,
        multiplier: Decimal,
        duration_minutes: int = 30,
    ) -> None:
        ends = datetime.now(timezone.utc) + timedelta(minutes=duration_minutes)
        await self.db.execute(
            """
            INSERT INTO active_events (guild_id, event_type, multiplier, ends_at)
            VALUES ($1, $2, $3, $4)
            """,
            guild_id,
            event_type,
            multiplier,
            ends,
        )
        logger.info("event_started", guild_id=guild_id, type=event_type, multiplier=str(multiplier))

    async def random_event(self, guild_id: int) -> str | None:
        if random.random() > 0.15:
            return None
        event_type = random.choice(EVENT_TYPES)
        multiplier = Decimal(str(round(random.uniform(1.5, 3.0), 2)))
        await self.start_event(guild_id, event_type, multiplier)
        return event_type

    async def cleanup_expired(self) -> int:
        result = await self.db.execute("DELETE FROM active_events WHERE ends_at <= NOW()")
        return int(result.split()[-1]) if result else 0
