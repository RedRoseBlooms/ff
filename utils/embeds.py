"""Discord embed builders with consistent branding."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import discord

from utils.currency import format_money

COLORS = {
    "success": 0x2ECC71,
    "error": 0xE74C3C,
    "gambling": 0xF1C40F,
    "economy": 0x3498DB,
    "events": 0x9B59B6,
    "admin": 0x2C3E50,
    "info": 0x5865F2,
}


def _footer(guild: discord.Guild | None = None) -> str:
    if guild and guild.icon:
        return f"{guild.name} • Premium Economy"
    return "Premium Economy Bot"


def base_embed(
    *,
    title: str,
    description: str | None = None,
    color_key: str = "economy",
    user: discord.User | discord.Member | None = None,
    guild: discord.Guild | None = None,
    fields: list[tuple[str, str, bool]] | None = None,
) -> discord.Embed:
    """Build a branded embed."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=COLORS.get(color_key, COLORS["economy"]),
        timestamp=datetime.now(timezone.utc),
    )
    if user:
        embed.set_thumbnail(url=user.display_avatar.url)
    if fields:
        for name, value, inline in fields:
            embed.add_field(name=name, value=value, inline=inline)
    embed.set_footer(text=_footer(guild), icon_url=guild.icon.url if guild and guild.icon else None)
    return embed


def success_embed(title: str, description: str, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"🟢 {title}", description=description, color_key="success", **kwargs)


def error_embed(title: str, description: str, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"🔴 {title}", description=description, color_key="error", **kwargs)


def gambling_embed(title: str, description: str | None = None, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"🎰 {title}", description=description, color_key="gambling", **kwargs)


def economy_embed(title: str, description: str | None = None, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"💵 {title}", description=description, color_key="economy", **kwargs)


def event_embed(title: str, description: str | None = None, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"🎉 {title}", description=description, color_key="events", **kwargs)


def admin_embed(title: str, description: str | None = None, **kwargs: Any) -> discord.Embed:
    return base_embed(title=f"⚙️ {title}", description=description, color_key="admin", **kwargs)


def balance_fields(wallet: Decimal, bank: Decimal) -> list[tuple[str, str, bool]]:
    total = wallet + bank
    return [
        ("Wallet", format_money(wallet), True),
        ("Bank", format_money(bank), True),
        ("Net Worth", format_money(total), True),
    ]
