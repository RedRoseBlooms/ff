"""Confirmation dialog view."""

from __future__ import annotations

from typing import Callable, Coroutine, Any

import discord

from views.base import BaseView


class ConfirmView(BaseView):
    def __init__(
        self,
        owner_id: int,
        on_confirm: Callable[[discord.Interaction], Coroutine[Any, Any, None]],
        *,
        timeout: float = 60.0,
    ) -> None:
        super().__init__(owner_id, timeout=timeout)
        self.on_confirm = on_confirm

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await self.on_confirm(interaction)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        await interaction.response.edit_message(content="Cancelled.", embed=None, view=self)
