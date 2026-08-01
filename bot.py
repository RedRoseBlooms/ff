"""
Discord Economy & Casino Bot — Production Entry Point
"""

from __future__ import annotations

import asyncio
import sys

import discord
from discord.ext import commands

from config import Config, load_config
from database.connection import Database
from services.economy_service import EconomyService
from services.event_service import EventService
from services.gambling_service import GamblingService
from services.house_edge_service import HouseEdgeService
from utils.logging import get_logger, setup_logging
from utils.rate_limit import InteractionLock, RateLimiter

COGS = [
    "cogs.economy",
    "cogs.gambling",
    "cogs.shop",
    "cogs.admin",
    "cogs.leaderboards",
    "cogs.help",
    "cogs.tasks",
]

logger = get_logger(__name__)


class EconomyBot(commands.Bot):
    """Custom bot with injected services."""

    def __init__(self, config: Config) -> None:
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = False
        super().__init__(command_prefix=config.command_prefix, intents=intents)
        self.config = config
        self.db = Database(config)
        self.rate_limiter = RateLimiter(max_calls=5, window_seconds=10)
        self.interaction_lock = InteractionLock()
        self.house_edge = HouseEdgeService(config)
        self.economy: EconomyService | None = None
        self.gambling: GamblingService | None = None
        self.events: EventService | None = None

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.db.run_schema()
        self.economy = EconomyService(self.db, self.config)
        self.gambling = GamblingService(self.db, self.economy, self.house_edge)
        self.events = EventService(self.db)

        for cog in COGS:
            await self.load_extension(cog)
            logger.info("cog_loaded", cog=cog)

        if self.config.guild_id:
            guild = discord.Object(id=self.config.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info("commands_synced", scope="guild", guild_id=self.config.guild_id)
        else:
            await self.tree.sync()
            logger.info("commands_synced", scope="global")

    async def on_ready(self) -> None:
        logger.info("bot_ready", user=str(self.user), guilds=len(self.guilds))

    async def close(self) -> None:
        await self.db.close()
        await super().close()


async def main() -> None:
    config = load_config()
    setup_logging(config.log_level)
    bot = EconomyBot(config)
    try:
        await bot.start(config.discord_token)
    except KeyboardInterrupt:
        logger.info("shutdown_requested")
    finally:
        await bot.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
