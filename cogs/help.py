"""Help command."""

from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.embeds import base_embed


class HelpCog(commands.Cog):
    @app_commands.command(name="help", description="View bot commands and features")
    async def help_cmd(self, interaction: discord.Interaction) -> None:
        embed = base_embed(
            title="📚 Premium Economy Bot",
            description="A full-featured economy & casino bot.",
            color_key="info",
            guild=interaction.guild,
            fields=[
                ("💵 Economy", "/balance /daily /weekly /monthly /work /crime /beg /rob /deposit /withdraw /pay /profile /stats /inventory", False),
                ("🎰 Gambling", "/gamble coinflip /gamble dice /gamble slots /gamble roulette /gamble blackjack /gamble higherlower /gamble baccarat /gamble limbo /gamble crash /gamble plinko /gamble mines /gamble tower /gamble duel", False),
                ("🛒 Shop", "/shop browse /buy", False),
                ("🏆 Leaderboards", "/leaderboard", False),
                ("⚙️ Admin", "/admin addmoney /admin stats /admin event", False),
            ],
        )
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog())
