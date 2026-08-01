"""Economy slash commands."""

from __future__ import annotations

from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from utils.currency import format_money, parse_bet
from utils.embeds import balance_fields, economy_embed, error_embed, success_embed
from utils.interactions import defer_if_slow


class EconomyCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    economy = app_commands.Group(name="economy", description="Economy commands")

    @app_commands.command(name="balance", description="Check your or another user's balance")
    @defer_if_slow()
    async def balance(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        record = await self.bot.economy.get_user(target.id, interaction.guild_id)
        embed = economy_embed(
            f"{target.display_name}'s Balance",
            user=target,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(record["wallet"])), Decimal(str(record["bank"]))),
        )
        embed.add_field(name="Level", value=str(record["level"]), inline=True)
        embed.add_field(name="XP", value=str(record["xp"]), inline=True)
        embed.add_field(name="Title", value=record["title"] or "Novice", inline=True)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily reward")
    @defer_if_slow()
    async def daily(self, interaction: discord.Interaction) -> None:
        updated, reward, streak = await self.bot.economy.claim_daily(
            interaction.user.id, interaction.guild_id
        )
        embed = success_embed(
            "Daily Reward",
            f"You received **{format_money(reward)}**!\n🔥 Streak: **{streak}** days",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="weekly", description="Claim your weekly reward")
    @defer_if_slow()
    async def weekly(self, interaction: discord.Interaction) -> None:
        updated, reward = await self.bot.economy.claim_weekly(interaction.user.id, interaction.guild_id)
        embed = success_embed(
            "Weekly Reward",
            f"You received **{format_money(reward)}**!",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="monthly", description="Claim your monthly reward")
    @defer_if_slow()
    async def monthly(self, interaction: discord.Interaction) -> None:
        updated, reward = await self.bot.economy.claim_monthly(interaction.user.id, interaction.guild_id)
        embed = success_embed(
            "Monthly Reward",
            f"You received **{format_money(reward)}**!",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="deposit", description="Deposit money into your bank")
    @defer_if_slow()
    async def deposit(self, interaction: discord.Interaction, amount: str) -> None:
        amt = parse_bet(amount)
        updated = await self.bot.economy.deposit(interaction.user.id, interaction.guild_id, amt)
        embed = success_embed(
            "Deposited",
            f"Deposited **{format_money(amt)}** to your bank.",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="withdraw", description="Withdraw money from your bank")
    @defer_if_slow()
    async def withdraw(self, interaction: discord.Interaction, amount: str) -> None:
        amt = parse_bet(amount)
        updated = await self.bot.economy.withdraw(interaction.user.id, interaction.guild_id, amt)
        embed = success_embed(
            "Withdrawn",
            f"Withdrew **{format_money(amt)}** to your wallet.",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pay", description="Pay another user")
    @defer_if_slow()
    async def pay(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        amount: str,
    ) -> None:
        amt = parse_bet(amount)
        sender, target, tax = await self.bot.economy.pay(
            interaction.user.id, interaction.guild_id, user.id, amt
        )
        embed = success_embed(
            "Payment Sent",
            f"Sent **{format_money(amt - tax)}** to {user.mention}\nTax: {format_money(tax)}",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(sender["wallet"])), Decimal(str(sender["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="work", description="Work for money")
    @defer_if_slow()
    async def work(self, interaction: discord.Interaction) -> None:
        updated, earned = await self.bot.economy.work(interaction.user.id, interaction.guild_id)
        embed = success_embed(
            "Work Complete",
            f"You earned **{format_money(earned)}**!",
            user=interaction.user,
            guild=interaction.guild,
            fields=balance_fields(Decimal(str(updated["wallet"])), Decimal(str(updated["bank"]))),
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="crime", description="Commit a crime for money")
    @defer_if_slow()
    async def crime(self, interaction: discord.Interaction) -> None:
        updated, amount, success = await self.bot.economy.crime(interaction.user.id, interaction.guild_id)
        if success:
            embed = success_embed(
                "Crime Successful",
                f"You got away with **{format_money(amount)}**!",
                user=interaction.user,
                guild=interaction.guild,
            )
        else:
            embed = error_embed(
                "Crime Failed",
                f"You were caught and fined **{format_money(amount)}**!",
                user=interaction.user,
                guild=interaction.guild,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="beg", description="Beg for spare change")
    @defer_if_slow()
    async def beg(self, interaction: discord.Interaction) -> None:
        updated, amount = await self.bot.economy.beg(interaction.user.id, interaction.guild_id)
        embed = success_embed(
            "Someone Gave You Money",
            f"You received **{format_money(amount)}**!",
            user=interaction.user,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="rob", description="Attempt to rob another user")
    @defer_if_slow()
    async def rob(self, interaction: discord.Interaction, user: discord.Member) -> None:
        updated, amount, success = await self.bot.economy.rob(
            interaction.user.id, interaction.guild_id, user.id
        )
        if success:
            embed = success_embed(
                "Rob Successful",
                f"You stole **{format_money(amount)}** from {user.display_name}!",
                user=interaction.user,
                guild=interaction.guild,
            )
        else:
            embed = error_embed(
                "Rob Failed",
                f"You were caught and lost **{format_money(amount)}**!",
                user=interaction.user,
                guild=interaction.guild,
            )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="profile", description="View your profile")
    @defer_if_slow()
    async def profile(self, interaction: discord.Interaction, user: discord.Member | None = None) -> None:
        target = user or interaction.user
        record = await self.bot.economy.get_user(target.id, interaction.guild_id)
        stats = await self.bot.db.fetchrow(
            "SELECT * FROM user_stats WHERE user_id = $1", target.id
        )
        embed = economy_embed(
            f"{target.display_name}'s Profile",
            user=target,
            guild=interaction.guild,
            fields=[
                ("Wallet", format_money(record["wallet"]), True),
                ("Bank", format_money(record["bank"]), True),
                ("Level", str(record["level"]), True),
                ("XP", str(record["xp"]), True),
                ("Prestige", str(record["prestige"]), True),
                ("Title", record["title"] or "Novice", True),
                ("Daily Streak", str(record["daily_streak"]), True),
                ("Win Streak", str(record["win_streak"]), True),
                ("Games Played", str(stats["games_played"] if stats else 0), True),
            ],
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats", description="View detailed statistics")
    @defer_if_slow()
    async def stats(self, interaction: discord.Interaction) -> None:
        stats = await self.bot.db.fetchrow(
            "SELECT * FROM user_stats WHERE user_id = $1", interaction.user.id
        )
        if not stats:
            await self.bot.economy.get_user(interaction.user.id, interaction.guild_id)
            stats = await self.bot.db.fetchrow(
                "SELECT * FROM user_stats WHERE user_id = $1", interaction.user.id
            )
        games = stats["games_played"] or 0
        won = stats["games_won"] or 0
        rate = f"{(won / games * 100):.1f}%" if games else "0%"
        embed = economy_embed(
            "Statistics",
            user=interaction.user,
            guild=interaction.guild,
            fields=[
                ("Money Earned", format_money(stats["money_earned"]), True),
                ("Money Lost", format_money(stats["money_lost"]), True),
                ("Net Profit", format_money(stats["money_earned"] - stats["money_lost"]), True),
                ("Games Played", str(games), True),
                ("Win Rate", rate, True),
                ("Biggest Win", format_money(stats["biggest_win"]), True),
                ("Biggest Loss", format_money(stats["biggest_loss"]), True),
            ],
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="inventory", description="View your inventory")
    @defer_if_slow()
    async def inventory(self, interaction: discord.Interaction) -> None:
        items = await self.bot.db.fetch(
            "SELECT * FROM inventory WHERE user_id = $1 ORDER BY acquired_at DESC",
            interaction.user.id,
        )
        if not items:
            desc = "Your inventory is empty."
        else:
            desc = "\n".join(f"• **{i['item_name']}** x{i['quantity']}" for i in items)
        embed = economy_embed("Inventory", desc, user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(EconomyCog(bot))
