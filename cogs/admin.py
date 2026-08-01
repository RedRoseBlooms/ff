"""Admin panel slash commands."""

from __future__ import annotations

from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from utils.currency import format_money, parse_bet
from utils.embeds import admin_embed, success_embed, error_embed
from utils.interactions import defer_if_slow


def is_admin_or_owner():
    async def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id in interaction.client.config.owner_ids:
            return True
        if interaction.user.guild_permissions.administrator:
            return True
        raise app_commands.CheckFailure("Admin only")

    return app_commands.check(predicate)


class AdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    admin = app_commands.Group(name="admin", description="Admin commands")

    @admin.command(name="addmoney", description="Add money to a user")
    @is_admin_or_owner()
    @defer_if_slow()
    async def addmoney(self, interaction: discord.Interaction, user: discord.Member, amount: str) -> None:
        amt = parse_bet(amount)
        async with self.bot.db.transaction() as conn:
            await self.bot.economy.users.get_or_create(user.id, interaction.guild_id)
            updated = await self.bot.economy.users.update_balance(conn, user.id, wallet_delta=amt)
            await self.bot.db.execute(
                """
                INSERT INTO audit_logs (guild_id, actor_id, action, target_id, details)
                VALUES ($1, $2, 'add_money', $3, $4::jsonb)
                """,
                interaction.guild_id,
                interaction.user.id,
                user.id,
                f'{{"amount": "{amt}"}}',
            )
        embed = admin_embed("Money Added", f"Added {format_money(amt)} to {user.mention}\nWallet: {format_money(updated['wallet'])}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="removemoney", description="Remove money from a user")
    @is_admin_or_owner()
    @defer_if_slow()
    async def removemoney(self, interaction: discord.Interaction, user: discord.Member, amount: str) -> None:
        amt = parse_bet(amount)
        async with self.bot.db.transaction() as conn:
            updated = await self.bot.economy.users.update_balance(conn, user.id, wallet_delta=-amt)
        embed = admin_embed("Money Removed", f"Removed {format_money(amt)} from {user.mention}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="setbalance", description="Set a user's wallet balance")
    @is_admin_or_owner()
    @defer_if_slow()
    async def setbalance(self, interaction: discord.Interaction, user: discord.Member, amount: str) -> None:
        amt = parse_bet(amount)
        async with self.bot.db.transaction() as conn:
            await self.bot.economy.users.get_or_create(user.id, interaction.guild_id)
            updated = await self.bot.economy.users.set_balance(conn, user.id, wallet=amt)
        embed = admin_embed("Balance Set", f"{user.mention} wallet set to {format_money(updated['wallet'])}")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="resetuser", description="Reset a user's economy data")
    @is_admin_or_owner()
    @defer_if_slow()
    async def resetuser(self, interaction: discord.Interaction, user: discord.Member) -> None:
        await self.bot.economy.users.reset_user(user.id)
        embed = admin_embed("User Reset", f"{user.mention} has been reset.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="stats", description="View economy statistics")
    @is_admin_or_owner()
    @defer_if_slow()
    async def stats(self, interaction: discord.Interaction) -> None:
        total_users = await self.bot.db.fetchval(
            "SELECT COUNT(*) FROM users WHERE guild_id = $1", interaction.guild_id
        )
        total_wallet = await self.bot.db.fetchval(
            "SELECT COALESCE(SUM(wallet), 0) FROM users WHERE guild_id = $1", interaction.guild_id
        )
        total_bank = await self.bot.db.fetchval(
            "SELECT COALESCE(SUM(bank), 0) FROM users WHERE guild_id = $1", interaction.guild_id
        )
        embed = admin_embed(
            "Economy Stats",
            fields=[
                ("Users", str(total_users), True),
                ("Total Wallet", format_money(total_wallet), True),
                ("Total Bank", format_money(total_bank), True),
                ("Combined", format_money(Decimal(str(total_wallet)) + Decimal(str(total_bank))), True),
            ],
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="event", description="Start a server event")
    @is_admin_or_owner()
    @defer_if_slow()
    async def event(
        self,
        interaction: discord.Interaction,
        event_type: str,
        multiplier: float,
        duration: app_commands.Range[int, 5, 1440] = 30,
    ) -> None:
        await self.bot.events.start_event(
            interaction.guild_id, event_type, Decimal(str(multiplier)), duration
        )
        embed = admin_embed("Event Started", f"**{event_type}** — {multiplier}x for {duration} minutes")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @admin.command(name="reload", description="Reload bot cogs")
    @is_admin_or_owner()
    async def reload(self, interaction: discord.Interaction) -> None:
        for ext in list(self.bot.extensions):
            await self.bot.reload_extension(ext)
        embed = admin_embed("Reloaded", "All cogs reloaded successfully.")
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
