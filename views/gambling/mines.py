"""Mines game interactive view - 5x4 grid."""

from __future__ import annotations

from decimal import Decimal

import discord

from services.gambling_service import GamblingService
from utils.currency import format_money
from utils.embeds import gambling_embed
from views.base import BaseView


class MinesView(BaseView):
    GRID_COLS = 5
    GRID_ROWS = 4
    TOTAL = GRID_COLS * GRID_ROWS

    def __init__(
        self,
        owner_id: int,
        guild_id: int,
        bet: Decimal,
        gambling: GamblingService,
        mine_positions: list[int],
        seed: str,
    ) -> None:
        super().__init__(owner_id, timeout=300.0)
        self.guild_id = guild_id
        self.bet = bet
        self.gambling = gambling
        self.mine_positions = set(mine_positions)
        self.seed = seed
        self.revealed: set[int] = set()
        self.game_over = False
        self._build_grid()

    def _build_grid(self) -> None:
        self.clear_items()
        for i in range(self.TOTAL):
            row, col = divmod(i, self.GRID_COLS)
            btn = discord.ui.Button(
                label="?",
                style=discord.ButtonStyle.secondary,
                row=row,
                custom_id=f"mine_{i}",
            )
            btn.callback = self._make_callback(i)
            self.add_item(btn)
        cashout = discord.ui.Button(
            label="💰 Cash Out",
            style=discord.ButtonStyle.success,
            row=self.GRID_ROWS,
            custom_id="cashout",
        )
        cashout.callback = self._cashout
        self.add_item(cashout)

    def _make_callback(self, index: int):
        async def callback(interaction: discord.Interaction) -> None:
            await self._reveal(interaction, index)

        return callback

    def _multiplier(self) -> Decimal:
        return self.gambling.mines_multiplier(len(self.revealed))

    def _embed(self, *, exploded: bool = False, won: bool = False) -> discord.Embed:
        mult = self._multiplier()
        potential = (self.bet * mult).quantize(Decimal("0.01"))
        desc = f"**Bet:** {format_money(self.bet)}\n**Multiplier:** {mult}x\n**Potential:** {format_money(potential)}"
        if exploded:
            return gambling_embed("Mines — BOOM!", desc + "\n\n💥 You hit a mine!")
        if won:
            return gambling_embed("Mines — Cashed Out!", desc + f"\n\n✅ Won {format_money(potential)}!")
        return gambling_embed("Mines", desc)

    async def _reveal(self, interaction: discord.Interaction, index: int) -> None:
        if self.game_over or index in self.revealed:
            await interaction.response.defer()
            return
        self.revealed.add(index)
        if index in self.mine_positions:
            self.game_over = True
            await self._explode(interaction)
            return
        btn = self._button_at(index)
        if btn:
            btn.label = "💎"
            btn.style = discord.ButtonStyle.success
            btn.disabled = True
        mult = self._multiplier()
        embed = gambling_embed(
            "Mines",
            f"**Bet:** {format_money(self.bet)}\n**Multiplier:** {mult}x\n**Tiles:** {len(self.revealed)}",
            user=interaction.user,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    def _button_at(self, index: int) -> discord.ui.Button | None:
        for item in self.children:
            if isinstance(item, discord.ui.Button) and item.custom_id == f"mine_{index}":
                return item
        return None

    async def _explode(self, interaction: discord.Interaction) -> None:
        for i in self.mine_positions:
            btn = self._button_at(i)
            if btn:
                btn.label = "💣"
                btn.style = discord.ButtonStyle.danger
                btn.disabled = True
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        await self.gambling.finalize_game(
            self.owner_id, self.guild_id, "mines", self.bet, Decimal("0"), False
        )
        embed = gambling_embed(
            "Mines — BOOM!",
            f"You hit a mine and lost {format_money(self.bet)}!",
            user=interaction.user,
        )
        await interaction.response.edit_message(embed=embed, view=self)

    async def _cashout(self, interaction: discord.Interaction) -> None:
        if self.game_over or len(self.revealed) == 0:
            await interaction.response.send_message("Reveal at least one tile first.", ephemeral=True)
            return
        self.game_over = True
        mult = self._multiplier()
        payout = (self.bet * mult).quantize(Decimal("0.01"))
        await self.gambling.finalize_game(
            self.owner_id, self.guild_id, "mines", self.bet, payout, True
        )
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        embed = gambling_embed(
            "Mines — Cashed Out!",
            f"**Multiplier:** {mult}x\n**Won:** {format_money(payout)}",
            user=interaction.user,
        )
        await interaction.response.edit_message(embed=embed, view=self)
