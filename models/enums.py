"""Shared enums and constants."""

from __future__ import annotations

from enum import StrEnum


class TransactionType(StrEnum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    WORK = "work"
    CRIME = "crime"
    BEG = "beg"
    ROB = "rob"
    PAY = "pay"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    GAMBLE_WIN = "gamble_win"
    GAMBLE_LOSS = "gamble_loss"
    SHOP_PURCHASE = "shop_purchase"
    ADMIN = "admin"
    EVENT = "event"
    TAX = "tax"


class GameType(StrEnum):
    COINFLIP = "coinflip"
    DICE = "dice"
    SLOTS = "slots"
    ROULETTE = "roulette"
    BLACKJACK = "blackjack"
    HIGHER_LOWER = "higher_lower"
    POKER = "poker"
    BACCARAT = "baccarat"
    MINES = "mines"
    CRASH = "crash"
    LIMBO = "limbo"
    TOWER = "tower"
    PLINKO = "plinko"
    DUEL = "duel"


class TicketStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    DELIVERED = "delivered"


class PurchaseStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    REFUNDED = "refunded"


COOLDOWNS = {
    "daily": 86400,
    "weekly": 604800,
    "monthly": 2592000,
    "work": 3600,
    "crime": 7200,
    "beg": 300,
    "rob": 14400,
    "pay": 10,
}

XP_PER_GAME = 5
XP_PER_WIN = 15
XP_PER_LEVEL = 100
