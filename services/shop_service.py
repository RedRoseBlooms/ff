"""Shop and ticket services."""

from __future__ import annotations

from decimal import Decimal

import asyncpg

from models.enums import PurchaseStatus, TransactionType
from repositories.shop_repository import ShopRepository
from repositories.transaction_repository import TransactionRepository
from repositories.user_repository import UserRepository
from utils.logging import get_logger

logger = get_logger(__name__)


class ShopService:
    def __init__(self, db) -> None:
        self.db = db
        self.shop = ShopRepository(db)
        self.users = UserRepository(db)
        self.transactions = TransactionRepository(db)

    async def purchase(
        self,
        user_id: int,
        guild_id: int,
        item_id: int,
    ) -> asyncpg.Record:
        item = await self.shop.get_item(item_id)
        if not item or not item["active"]:
            raise ValueError("Item not found")
        if item["guild_id"] != guild_id:
            raise ValueError("Item not available in this server")
        price = Decimal(str(item["price"]))
        async with self.db.transaction() as conn:
            user = await self.users.get_or_create(user_id, guild_id)
            if Decimal(str(user["wallet"])) < price:
                raise ValueError("Insufficient funds")
            await self.users.update_balance(conn, user_id, wallet_delta=-price)
            purchase = await self.shop.create_purchase(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                shop_item_id=item_id,
                item_name=item["name"],
                price=price,
            )
            updated = await conn.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=-price,
                balance_after=Decimal(str(updated["wallet"])) + Decimal(str(updated["bank"])),
                tx_type=TransactionType.SHOP_PURCHASE,
                description=f"Purchased {item['name']}",
                metadata={"purchase_id": str(purchase["purchase_id"])},
            )
            if item["stock"] > 0:
                await conn.execute(
                    "UPDATE shop_items SET stock = stock - 1 WHERE id = $1 AND stock > 0",
                    item_id,
                )
        logger.info("shop_purchase", user_id=user_id, item=item["name"], price=str(price))
        return purchase


class TicketService:
    def __init__(self, db) -> None:
        self.db = db

    async def create_ticket_record(
        self,
        channel_id: int,
        user_id: int,
        guild_id: int,
        purchase_id: str,
    ) -> None:
        await self.db.execute(
            """
            INSERT INTO tickets (channel_id, purchase_id, user_id, guild_id)
            VALUES ($1, $2::uuid, $3, $4)
            """,
            channel_id,
            purchase_id,
            user_id,
            guild_id,
        )
        await self.db.execute(
            "UPDATE purchases SET ticket_channel_id = $1, status = $2 WHERE purchase_id = $3::uuid",
            channel_id,
            PurchaseStatus.PROCESSING,
            purchase_id,
        )

    async def close_ticket(self, channel_id: int, transcript: str = "") -> None:
        await self.db.execute(
            """
            UPDATE tickets SET status = 'closed', transcript = $2, closed_at = NOW()
            WHERE channel_id = $1
            """,
            channel_id,
            transcript,
        )
