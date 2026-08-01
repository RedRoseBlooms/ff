"""Discord interaction helpers."""

from __future__ import annotations

import functools
from typing import Callable, Coroutine, Any

import discord
from discord import app_commands

from utils.embeds import error_embed


def defer_if_slow(threshold: bool = True):
    """Decorator to defer interactions that may take time."""

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not interaction.response.is_done():
                await interaction.response.defer(thinking=threshold)
            try:
                return await func(self, interaction, *args, **kwargs)
            except ValueError as e:
                embed = error_embed("Error", str(e))
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)
            except discord.HTTPException:
                embed = error_embed("Discord Error", "Something went wrong. Please try again.")
                if interaction.response.is_done():
                    await interaction.followup.send(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=embed, ephemeral=True)

        return wrapper

    return decorator


async def safe_edit(interaction: discord.Interaction, **kwargs: Any) -> None:
    """Edit message safely handling expired interactions."""
    try:
        if interaction.response.is_done():
            if interaction.message:
                await interaction.message.edit(**kwargs)
            else:
                await interaction.edit_original_response(**kwargs)
        else:
            await interaction.response.edit_message(**kwargs)
    except discord.HTTPException:
        pass
