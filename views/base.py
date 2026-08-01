"""Base interactive view with ownership and timeout handling."""

from __future__ import annotations

import discord


class BaseView(discord.ui.View):
    """View that disables on timeout and validates owner."""

    def __init__(self, owner_id: int, *, timeout: float = 120.0) -> None:
        super().__init__(timeout=timeout)
        self.owner_id = owner_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.owner_id:
            await interaction.response.send_message(
                "This interaction isn't for you.", ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button | discord.ui.Select):
                item.disabled = True
