"""User data access layer."""

from __future__ import annotations

from decimal import Decimal

import asyncpg

from config import Config


class UserRepository:
    """CRUD operations for users table."""

    def __init__(self, db) -> None:
        self.db = db
        self.config: Config = db.config

    async def get_or_create(self, user_id: int, guild_id: int) -> asyncpg.Record:
        row = await self.db.fetchrow(
            "SELECT * FROM users WHERE user_id = $1",
            user_id,
        )
        if row:
            return row
        return await self.db.fetchrow(
            """
            INSERT INTO users (user_id, guild_id, wallet)
            VALUES ($1, $2, $3)
            RETURNING *
            """,
            user_id,
            guild_id,
            self.config.starting_balance,
        )

    async def get(self, user_id: int) -> asyncpg.Record | None:
        return await self.db.fetchrow("SELECT * FROM users WHERE user_id = $1", user_id)

    async def update_balance(
        self,
        conn: asyncpg.Connection,
        user_id: int,
        *,
        wallet_delta: Decimal = Decimal("0"),
        bank_delta: Decimal = Decimal("0"),
    ) -> asyncpg.Record:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET wallet = wallet + $2,
                bank = bank + $3,
                updated_at = NOW()
            WHERE user_id = $1
              AND wallet + $2 >= 0
              AND bank + $3 >= 0
            RETURNING *
            """,
            user_id,
            wallet_delta,
            bank_delta,
        )
        if not row:
            raise ValueError("Insufficient funds or user not found")
        return row

    async def set_balance(
        self,
        conn: asyncpg.Connection,
        user_id: int,
        *,
        wallet: Decimal | None = None,
        bank: Decimal | None = None,
    ) -> asyncpg.Record:
        if wallet is not None and bank is not None:
            return await conn.fetchrow(
                """
                UPDATE users SET wallet = $2, bank = $3, updated_at = NOW()
                WHERE user_id = $1 RETURNING *
                """,
                user_id,
                wallet,
                bank,
            )
        if wallet is not None:
            return await conn.fetchrow(
                "UPDATE users SET wallet = $2, updated_at = NOW() WHERE user_id = $1 RETURNING *",
                user_id,
                wallet,
            )
        if bank is not None:
            return await conn.fetchrow(
                "UPDATE users SET bank = $2, updated_at = NOW() WHERE user_id = $1 RETURNING *",
                user_id,
                bank,
            )
        raise ValueError("Must specify wallet or bank")

    async def add_xp(self, conn: asyncpg.Connection, user_id: int, xp: int) -> asyncpg.Record:
        row = await conn.fetchrow(
            """
            UPDATE users
            SET xp = xp + $2,
                level = GREATEST(1, 1 + (xp + $2) / 100),
                updated_at = NOW()
            WHERE user_id = $1
            RETURNING *
            """,
            user_id,
            xp,
        )
        return row

    async def update_cooldown(self, user_id: int, field: str) -> None:
        allowed = {"last_daily", "last_weekly", "last_monthly", "last_work", "last_crime", "last_beg", "last_rob"}
        if field not in allowed:
            raise ValueError("Invalid cooldown field")
        await self.db.execute(
            f"UPDATE users SET {field} = NOW(), updated_at = NOW() WHERE user_id = $1",
            user_id,
        )

    async def increment_streak(self, user_id: int, streak_field: str) -> int:
        if streak_field not in {"daily_streak", "weekly_streak", "win_streak"}:
            raise ValueError("Invalid streak field")
        return await self.db.fetchval(
            f"""
            UPDATE users SET {streak_field} = {streak_field} + 1, updated_at = NOW()
            WHERE user_id = $1 RETURNING {streak_field}
            """,
            user_id,
        )

    async def reset_user(self, user_id: int) -> None:
        await self.db.execute(
            """
            UPDATE users SET
                wallet = $2, bank = 0, xp = 0, level = 1, prestige = 0,
                title = 'Novice', daily_streak = 0, weekly_streak = 0,
                win_streak = 0, best_win_streak = 0, updated_at = NOW()
            WHERE user_id = $1
            """,
            user_id,
            self.config.starting_balance,
        )

    async def leaderboard(
        self,
        guild_id: int,
        column: str,
        limit: int = 10,
        offset: int = 0,
    ) -> list[asyncpg.Record]:
        allowed = {"wallet", "level", "prestige", "win_streak", "best_win_streak"}
        if column not in allowed:
            raise ValueError("Invalid leaderboard column")
        return await self.db.fetch(
            f"""
            SELECT user_id, wallet, bank, level, prestige, win_streak, best_win_streak
            FROM users WHERE guild_id = $1
            ORDER BY {column} DESC
            LIMIT $2 OFFSET $3
            """,
            guild_id,
            limit,
            offset,
        )
