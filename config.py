"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import FrozenSet

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(raw: str | None) -> FrozenSet[int]:
    if not raw:
        return frozenset()
    return frozenset(int(x.strip()) for x in raw.split(",") if x.strip().isdigit())


def _decimal(value: str | None, default: str) -> Decimal:
    return Decimal(value or default)


@dataclass(frozen=True, slots=True)
class Config:
    """Immutable runtime configuration."""

    discord_token: str
    database_url: str
    environment: str
    log_level: str
    owner_ids: FrozenSet[int]
    guild_id: int | None
    staff_role_id: int | None
    ticket_category_id: int | None
    log_channel_id: int | None
    starting_balance: Decimal
    daily_reward: Decimal
    weekly_reward: Decimal
    monthly_reward: Decimal
    command_prefix: str = "!"
    pool_min_size: int = 5
    pool_max_size: int = 50
    cache_ttl_seconds: int = 60
    max_bet_multiplier: Decimal = field(default=Decimal("1.00"))
    rob_success_rate: float = 0.35
    crime_success_rate: float = 0.45
    work_min: Decimal = field(default=Decimal("0.01"))
    work_max: Decimal = field(default=Decimal("0.05"))
    pay_tax_rate: Decimal = field(default=Decimal("0.02"))
    house_edge_base: Decimal = field(default=Decimal("0.03"))


def load_config() -> Config:
    """Load and validate configuration."""
    token = os.getenv("DISCORD_TOKEN", "")
    if not token:
        raise ValueError("DISCORD_TOKEN is required")

    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise ValueError("DATABASE_URL is required")

    guild_raw = os.getenv("DISCORD_GUILD_ID")
    guild_id = int(guild_raw) if guild_raw and guild_raw.isdigit() else None

    staff_raw = os.getenv("STAFF_ROLE_ID")
    staff_role_id = int(staff_raw) if staff_raw and staff_raw.isdigit() else None

    ticket_raw = os.getenv("TICKET_CATEGORY_ID")
    ticket_category_id = int(ticket_raw) if ticket_raw and ticket_raw.isdigit() else None

    log_raw = os.getenv("LOG_CHANNEL_ID")
    log_channel_id = int(log_raw) if log_raw and log_raw.isdigit() else None

    return Config(
        discord_token=token,
        database_url=db_url,
        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        owner_ids=_parse_ids(os.getenv("BOT_OWNER_IDS")),
        guild_id=guild_id,
        staff_role_id=staff_role_id,
        ticket_category_id=ticket_category_id,
        log_channel_id=log_channel_id,
        starting_balance=_decimal(os.getenv("STARTING_BALANCE"), "0.10"),
        daily_reward=_decimal(os.getenv("DAILY_REWARD"), "0.10"),
        weekly_reward=_decimal(os.getenv("WEEKLY_REWARD"), "1.00"),
        monthly_reward=_decimal(os.getenv("MONTHLY_REWARD"), "5.00"),
    )
