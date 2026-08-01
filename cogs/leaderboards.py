"""Interactive leaderboard commands."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.currency import format_money
from utils.embeds import economy_embed
from utils.interactions import defer_if_slow
from views.pagination import PaginatorView

LEADERBOARDS = {
    "richest": ("wallet", "Richest Players"),
    "level": ("level", "Highest Level"),
    "prestige": ("prestige", "Highest Prestige"),
    "win_streak": ("best_win_streak", "Best Win Streak"),
}


class LeaderboardsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="leaderboard", description="View server leaderboards")
    @app_commands.choices(board=[
        app_commands.Choice(name="Richest", value="richest"),
        app_commands.Choice(name="Highest Level", value="level"),
        app_commands.Choice(name="Highest Prestige", value="prestige"),
        app_commands.Choice(name="Biggest Win", value="biggest_win"),
        app_commands.Choice(name="Most Games", value="most_games"),
        app_commands.Choice(name="Net Profit", value="net_profit"),
        app_commands.Choice(name="Best Win Streak", value="win_streak"),
    ])
    @defer_if_slow()
    async def leaderboard(
        self,
        interaction: discord.Interaction,
        board: app_commands.Choice[str],
    ) -> None:
        guild_id = interaction.guild_id
        pages: list[discord.Embed] = []
        per_page = 10

        if board.value in LEADERBOARDS:
            column, title = LEADERBOARDS[board.value]
            for page in range(3):
                rows = await self.bot.economy.users.leaderboard(
                    guild_id, column, limit=per_page, offset=page * per_page
                )
                if not rows:
                    break
                lines = []
                for i, row in enumerate(rows, start=page * per_page + 1):
                    val = row[column]
                    if column == "wallet":
                        val = format_money(row["wallet"] + row["bank"])
                    lines.append(f"`#{i}` <@{row['user_id']}> — **{val}**")
                embed = economy_embed(title, "\n".join(lines), guild=interaction.guild)
                pages.append(embed)
        else:
            for page in range(3):
                rows = await self.bot.gambling.games.leaderboard(
                    guild_id, board.value, limit=per_page, offset=page * per_page
                )
                if not rows:
                    break
                lines = []
                for i, row in enumerate(rows, start=page * per_page + 1):
                    val = row["value"]
                    if board.value in ("biggest_win", "net_profit"):
                        val = format_money(val)
                    lines.append(f"`#{i}` <@{row['user_id']}> — **{val}**")
                embed = economy_embed(board.name, "\n".join(lines), guild=interaction.guild)
                pages.append(embed)

        if not pages:
            pages = [economy_embed("Leaderboard", "No data yet.", guild=interaction.guild)]

        view = PaginatorView(interaction.user.id, pages)
        await interaction.followup.send(embed=view.current, view=view if len(pages) > 1 else None)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaderboardsCog(bot))
