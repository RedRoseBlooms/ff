"""Background tasks for events and maintenance."""

from __future__ import annotations

import discord
from discord.ext import commands, tasks

from utils.embeds import event_embed


class TasksCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.event_loop.start()
        self.cleanup_loop.start()

    def cog_unload(self) -> None:
        self.event_loop.cancel()
        self.cleanup_loop.cancel()

    @tasks.loop(minutes=30)
    async def event_loop(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            try:
                event_type = await self.bot.events.random_event(guild.id)
                if event_type and guild.system_channel:
                    embed = event_embed(
                        "Server Event!",
                        f"**{event_type.replace('_', ' ').title()}** is now active!",
                    )
                    await guild.system_channel.send(embed=embed)
            except discord.HTTPException:
                pass

    @tasks.loop(hours=1)
    async def cleanup_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self.bot.events.cleanup_expired()

    @event_loop.before_loop
    @cleanup_loop.before_loop
    async def before(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(TasksCog(bot))
