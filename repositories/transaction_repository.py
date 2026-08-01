"""Transaction logging repository."""

from __future__ import annotations

from decimal import Decimal
import json

import asyncpg

from models.enums import TransactionType


class TransactionRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def log(
        self,
        conn: asyncpg.Connection,
        *,
        user_id: int,
        guild_id: int,
        amount: Decimal,
        balance_after: Decimal,
        tx_type: TransactionType | str,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        await conn.execute(
            """
            INSERT INTO transactions (user_id, guild_id, amount, balance_after, tx_type, description, metadata)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb)
            """,
            user_id,
            guild_id,
            amount,
            balance_after,
            str(tx_type),
            description,
            json.dumps(metadata or {}),
        )

    async def recent(self, user_id: int, limit: int = 10) -> list[asyncpg.Record]:
        return await self.db.fetch(
            """
            SELECT * FROM transactions WHERE user_id = $1
            ORDER BY created_at DESC LIMIT $2
            """,
            user_id,
            limit,
        )
