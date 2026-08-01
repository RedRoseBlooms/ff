"""Pytest configuration."""

import pytest


@pytest.fixture
def sample_config():
    from decimal import Decimal
    from config import Config

    return Config(
        discord_token="test",
        database_url="postgresql://test",
        environment="test",
        log_level="DEBUG",
        owner_ids=frozenset({123}),
        guild_id=None,
        staff_role_id=None,
        ticket_category_id=None,
        log_channel_id=None,
        starting_balance=Decimal("0.10"),
        daily_reward=Decimal("0.10"),
        weekly_reward=Decimal("1.00"),
        monthly_reward=Decimal("5.00"),
    )
