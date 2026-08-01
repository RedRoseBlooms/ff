"""Shop and purchase repository."""

from __future__ import annotations

import json
from decimal import Decimal

import asyncpg


class ShopRepository:
    def __init__(self, db) -> None:
        self.db = db

    async def list_items(self, guild_id: int) -> list[asyncpg.Record]:
        return await self.db.fetch(
            """
            SELECT * FROM shop_items
            WHERE guild_id = $1 AND active = TRUE
            ORDER BY category, price
            """,
            guild_id,
        )

    async def get_item(self, item_id: int) -> asyncpg.Record | None:
        return await self.db.fetchrow("SELECT * FROM shop_items WHERE id = $1", item_id)

    async def add_item(
        self,
        guild_id: int,
        name: str,
        price: Decimal,
        description: str = "",
        category: str = "general",
        stock: int = -1,
    ) -> asyncpg.Record:
        return await self.db.fetchrow(
            """
            INSERT INTO shop_items (guild_id, name, description, price, category, stock)
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING *
            """,
            guild_id,
            name,
            description,
            price,
            category,
            stock,
        )

    async def remove_item(self, item_id: int) -> None:
        await self.db.execute("UPDATE shop_items SET active = FALSE WHERE id = $1", item_id)

    async def edit_item(self, item_id: int, **fields) -> asyncpg.Record | None:
        allowed = {"name", "description", "price", "category", "stock", "active"}
        updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
        if not updates:
            return await self.get_item(item_id)
        sets = ", ".join(f"{k} = ${i+2}" for i, k in enumerate(updates))
        values = list(updates.values())
        return await self.db.fetchrow(
            f"UPDATE shop_items SET {sets} WHERE id = $1 RETURNING *",
            item_id,
            *values,
        )

    async def create_purchase(
        self,
        conn: asyncpg.Connection,
        *,
        user_id: int,
        guild_id: int,
        shop_item_id: int,
        item_name: str,
        price: Decimal,
        metadata: dict | None = None,
    ) -> asyncpg.Record:
        return await conn.fetchrow(
            """
            INSERT INTO purchases (user_id, guild_id, shop_item_id, item_name, price, metadata)
            VALUES ($1, $2, $3, $4, $5, $6::jsonb)
            RETURNING *
            """,
            user_id,
            guild_id,
            shop_item_id,
            item_name,
            price,
            json.dumps(metadata or {}),
        )

    async def seed_defaults(self, guild_id: int) -> None:
        await self.db.execute("SELECT seed_default_shop($1)", guild_id)
