"""Core economy business logic."""

from __future__ import annotations

import random
from datetime import datetime, timezone
from decimal import Decimal

import asyncpg

from config import Config
from models.enums import TransactionType
from repositories.transaction_repository import TransactionRepository
from repositories.user_repository import UserRepository
from services.house_edge_service import HouseEdgeService
from utils.logging import get_logger

logger = get_logger(__name__)


class EconomyService:
    """Handles all economy operations with atomic transactions."""

    def __init__(self, db, config: Config) -> None:
        self.db = db
        self.config = config
        self.users = UserRepository(db)
        self.transactions = TransactionRepository(db)
        self.house_edge = HouseEdgeService(config)

    async def get_user(self, user_id: int, guild_id: int) -> asyncpg.Record:
        return await self.users.get_or_create(user_id, guild_id)

    def _net_worth(self, user: asyncpg.Record) -> Decimal:
        return Decimal(str(user["wallet"])) + Decimal(str(user["bank"]))

    async def _reward(
        self,
        user_id: int,
        guild_id: int,
        amount: Decimal,
        tx_type: TransactionType,
        cooldown_field: str,
        streak_field: str | None = None,
    ) -> tuple[asyncpg.Record, Decimal]:
        async with self.db.transaction() as conn:
            user = await self.users.get_or_create(user_id, guild_id)
            updated = await self.users.update_balance(conn, user_id, wallet_delta=amount)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=amount,
                balance_after=Decimal(str(updated["wallet"])) + Decimal(str(updated["bank"])),
                tx_type=tx_type,
                description=f"{tx_type.value} reward",
            )
            await conn.execute(
                f"UPDATE users SET {cooldown_field} = NOW(), updated_at = NOW() WHERE user_id = $1",
                user_id,
            )
            if streak_field:
                await conn.execute(
                    f"UPDATE users SET {streak_field} = {streak_field} + 1 WHERE user_id = $1",
                    user_id,
                )
        logger.info("economy_reward", user_id=user_id, amount=str(amount), type=tx_type.value)
        return updated, amount

    def _cooldown_remaining(self, last: datetime | None, duration: int) -> int:
        if not last:
            return 0
        if last.tzinfo is None:
            last = last.replace(tzinfo=timezone.utc)
        elapsed = (datetime.now(timezone.utc) - last).total_seconds()
        return max(0, int(duration - elapsed))

    async def claim_daily(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal, int]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_daily"], 86400)
        if remaining > 0:
            raise ValueError(f"Daily on cooldown: {remaining}s")
        amount = self.config.daily_reward
        updated, reward = await self._reward(
            user_id, guild_id, amount, TransactionType.DAILY, "last_daily", "daily_streak"
        )
        return updated, reward, user["daily_streak"] + 1

    async def claim_weekly(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_weekly"], 604800)
        if remaining > 0:
            raise ValueError(f"Weekly on cooldown: {remaining}s")
        updated, reward = await self._reward(
            user_id, guild_id, self.config.weekly_reward, TransactionType.WEEKLY, "last_weekly", "weekly_streak"
        )
        return updated, reward

    async def claim_monthly(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_monthly"], 2592000)
        if remaining > 0:
            raise ValueError(f"Monthly on cooldown: {remaining}s")
        updated, reward = await self._reward(
            user_id, guild_id, self.config.monthly_reward, TransactionType.MONTHLY, "last_monthly"
        )
        return updated, reward

    async def work(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_work"], 3600)
        if remaining > 0:
            raise ValueError(f"Work on cooldown: {remaining}s")
        amount = Decimal(str(round(random.uniform(float(self.config.work_min), float(self.config.work_max)), 2)))
        return (await self._reward(user_id, guild_id, amount, TransactionType.WORK, "last_work"))[0], amount

    async def crime(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal, bool]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_crime"], 7200)
        if remaining > 0:
            raise ValueError(f"Crime on cooldown: {remaining}s")
        success = random.random() < self.config.crime_success_rate
        if success:
            amount = Decimal(str(round(random.uniform(0.05, 0.25), 2)))
            updated, _ = await self._reward(user_id, guild_id, amount, TransactionType.CRIME, "last_crime")
            return updated, amount, True
        fine = min(Decimal(str(user["wallet"])), Decimal("0.10"))
        async with self.db.transaction() as conn:
            updated = await self.users.update_balance(conn, user_id, wallet_delta=-fine)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=-fine,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.CRIME,
                description="Crime failed - fine",
            )
            await conn.execute("UPDATE users SET last_crime = NOW() WHERE user_id = $1", user_id)
        return updated, fine, False

    async def beg(self, user_id: int, guild_id: int) -> tuple[asyncpg.Record, Decimal]:
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_beg"], 300)
        if remaining > 0:
            raise ValueError(f"Beg on cooldown: {remaining}s")
        amount = Decimal(str(round(random.uniform(0.01, 0.05), 2)))
        updated, _ = await self._reward(user_id, guild_id, amount, TransactionType.BEG, "last_beg")
        return updated, amount

    async def rob(self, user_id: int, guild_id: int, target_id: int) -> tuple[asyncpg.Record, Decimal, bool]:
        if user_id == target_id:
            raise ValueError("You cannot rob yourself")
        user = await self.get_user(user_id, guild_id)
        remaining = self._cooldown_remaining(user["last_rob"], 14400)
        if remaining > 0:
            raise ValueError(f"Rob on cooldown: {remaining}s")
        target = await self.get_user(target_id, guild_id)
        target_wallet = Decimal(str(target["wallet"]))
        if target_wallet < Decimal("0.05"):
            raise ValueError("Target is too poor to rob")
        success = random.random() < self.config.rob_success_rate
        async with self.db.transaction() as conn:
            if success:
                steal = min(target_wallet * Decimal("0.15"), Decimal("1.00"))
                await self.users.update_balance(conn, target_id, wallet_delta=-steal)
                updated = await self.users.update_balance(conn, user_id, wallet_delta=steal)
                await self.transactions.log(
                    conn,
                    user_id=user_id,
                    guild_id=guild_id,
                    amount=steal,
                    balance_after=self._net_worth(updated),
                    tx_type=TransactionType.ROB,
                    description=f"Robbed user {target_id}",
                )
                await conn.execute("UPDATE users SET last_rob = NOW() WHERE user_id = $1", user_id)
                return updated, steal, True
            fine = min(Decimal(str(user["wallet"])), Decimal("0.20"))
            updated = await self.users.update_balance(conn, user_id, wallet_delta=-fine)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=-fine,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.ROB,
                description="Rob failed - caught",
            )
            await conn.execute("UPDATE users SET last_rob = NOW() WHERE user_id = $1", user_id)
            return updated, fine, False

    async def deposit(self, user_id: int, guild_id: int, amount: Decimal) -> asyncpg.Record:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        async with self.db.transaction() as conn:
            user = await self.users.get_or_create(user_id, guild_id)
            if Decimal(str(user["wallet"])) < amount:
                raise ValueError("Insufficient wallet balance")
            updated = await self.users.update_balance(conn, user_id, wallet_delta=-amount, bank_delta=amount)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=amount,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.DEPOSIT,
            )
        return updated

    async def withdraw(self, user_id: int, guild_id: int, amount: Decimal) -> asyncpg.Record:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        async with self.db.transaction() as conn:
            user = await self.users.get_or_create(user_id, guild_id)
            if Decimal(str(user["bank"])) < amount:
                raise ValueError("Insufficient bank balance")
            updated = await self.users.update_balance(conn, user_id, wallet_delta=amount, bank_delta=-amount)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=amount,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.WITHDRAW,
            )
        return updated

    async def pay(
        self,
        user_id: int,
        guild_id: int,
        target_id: int,
        amount: Decimal,
    ) -> tuple[asyncpg.Record, asyncpg.Record, Decimal]:
        if amount <= 0:
            raise ValueError("Amount must be positive")
        if user_id == target_id:
            raise ValueError("Cannot pay yourself")
        tax = (amount * self.config.pay_tax_rate).quantize(Decimal("0.01"))
        received = amount - tax
        async with self.db.transaction() as conn:
            sender = await self.users.get_or_create(user_id, guild_id)
            if Decimal(str(sender["wallet"])) < amount:
                raise ValueError("Insufficient funds")
            await self.users.get_or_create(target_id, guild_id)
            sender_up = await self.users.update_balance(conn, user_id, wallet_delta=-amount)
            target_up = await self.users.update_balance(conn, target_id, wallet_delta=received)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=-amount,
                balance_after=self._net_worth(sender_up),
                tx_type=TransactionType.PAY,
                description=f"Paid {target_id}",
            )
            await self.transactions.log(
                conn,
                user_id=target_id,
                guild_id=guild_id,
                amount=received,
                balance_after=self._net_worth(target_up),
                tx_type=TransactionType.PAY,
                description=f"Received from {user_id}",
            )
        return sender_up, target_up, tax

    async def deduct_bet(self, user_id: int, guild_id: int, amount: Decimal) -> asyncpg.Record:
        async with self.db.transaction() as conn:
            updated = await self.users.update_balance(conn, user_id, wallet_delta=-amount)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=-amount,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.GAMBLE_LOSS,
                description="Bet placed",
            )
        return updated

    async def payout_win(
        self,
        user_id: int,
        guild_id: int,
        bet: Decimal,
        payout: Decimal,
        game_type: str,
    ) -> asyncpg.Record:
        async with self.db.transaction() as conn:
            updated = await self.users.update_balance(conn, user_id, wallet_delta=payout)
            await self.transactions.log(
                conn,
                user_id=user_id,
                guild_id=guild_id,
                amount=payout,
                balance_after=self._net_worth(updated),
                tx_type=TransactionType.GAMBLE_WIN,
                description=f"{game_type} win",
            )
        return updated

    def max_bet(self, user: asyncpg.Record) -> Decimal:
        wallet = Decimal(str(user["wallet"]))
        cap = wallet * self.config.max_bet_multiplier
        return max(Decimal("0.01"), min(wallet, cap if cap > 0 else wallet))
