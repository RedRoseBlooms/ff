"""Paginated embed view."""

from __future__ import annotations

import discord

from views.base import BaseView


class PaginatorView(BaseView):
    def __init__(
        self,
        owner_id: int,
        pages: list[discord.Embed],
        *,
        timeout: float = 180.0,
    ) -> None:
        super().__init__(owner_id, timeout=timeout)
        self.pages = pages
        self.index = 0
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.prev_btn.disabled = self.index <= 0
        self.next_btn.disabled = self.index >= len(self.pages) - 1

    @property
    def current(self) -> discord.Embed:
        embed = self.pages[self.index]
        embed.set_footer(text=f"Page {self.index + 1}/{len(self.pages)} • {embed.footer.text or ''}")
        return embed

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = max(0, self.index - 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.current, view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        self.index = min(len(self.pages) - 1, self.index + 1)
        self._sync_buttons()
        await interaction.response.edit_message(embed=self.current, view=self)

    @discord.ui.button(label="🔄 Refresh", style=discord.ButtonStyle.primary)
    async def refresh_btn(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.edit_message(embed=self.current, view=self)
