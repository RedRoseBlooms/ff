"""Gambling slash commands and animated games."""

from __future__ import annotations

import asyncio
from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from models.enums import GameType
from utils.currency import format_money, parse_bet
from utils.embeds import gambling_embed, success_embed, error_embed
from utils.interactions import defer_if_slow
from views.gambling.mines import MinesView


class GamblingCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    gamble = app_commands.Group(name="gamble", description="Casino games")

    @gamble.command(name="coinflip", description="Flip a coin")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails"),
    ])
    @defer_if_slow()
    async def coinflip(
        self,
        interaction: discord.Interaction,
        bet: str,
        choice: app_commands.Choice[str],
    ) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Coinflip", "🪙 Flipping...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        for frame in ["🪙 ·", "· 🪙", "🪙 ·"]:
            embed.description = frame
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)
        result = await self.bot.gambling.coinflip(interaction.user.id, interaction.guild_id, amount, choice.value)
        if result["won"]:
            embed = success_embed("Coinflip Win!", f"**{result['result'].title()}** — Won {format_money(result['payout'])}!", user=interaction.user, guild=interaction.guild)
        else:
            embed = error_embed("Coinflip Loss", f"**{result['result'].title()}** — Lost {format_money(amount)}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="dice", description="Roll dice — win if roll >= target")
    @defer_if_slow()
    async def dice(self, interaction: discord.Interaction, bet: str, target: app_commands.Range[int, 2, 6]) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Dice", "🎲 Rolling...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        for i in range(1, 4):
            embed.description = f"🎲 Rolling... `{i}`"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.3)
        result = await self.bot.gambling.dice(interaction.user.id, interaction.guild_id, amount, target)
        status = "Win" if result["won"] else "Loss"
        fn = success_embed if result["won"] else error_embed
        embed = fn(f"Dice {status}", f"Rolled **{result['roll']}** (target ≥ {target})\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="slots", description="Spin the slot machine")
    @defer_if_slow()
    async def slots(self, interaction: discord.Interaction, bet: str) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Slots", "🎰 Spinning...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        for _ in range(5):
            reels = ["❓", "❓", "❓"]
            embed.description = " | ".join(reels)
            await msg.edit(embed=embed)
            await asyncio.sleep(0.25)
        result = await self.bot.gambling.slots(interaction.user.id, interaction.guild_id, amount)
        reels = " | ".join(result["reels"])
        fn = success_embed if result["won"] else error_embed
        embed = fn("Slots", f"{reels}\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="roulette", description="Play roulette")
    @defer_if_slow()
    async def roulette(self, interaction: discord.Interaction, bet: str, choice: str) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Roulette", "🎡 Spinning...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        for n in [12, 27, 3, 19, 0]:
            embed.description = f"🎡 `{n}`"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.3)
        result = await self.bot.gambling.roulette(interaction.user.id, interaction.guild_id, amount, choice)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Roulette", f"**{result['number']}** ({result['color']})\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="limbo", description="Set a target multiplier")
    @defer_if_slow()
    async def limbo(self, interaction: discord.Interaction, bet: str, target: float) -> None:
        if target < 1.01 or target > 100:
            raise ValueError("Target must be between 1.01 and 100")
        amount = parse_bet(bet)
        result = await self.bot.gambling.limbo(interaction.user.id, interaction.guild_id, amount, Decimal(str(target)))
        fn = success_embed if result["won"] else error_embed
        embed = fn("Limbo", f"Result: **{result['result']}x** (target {result['target']}x)\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @gamble.command(name="crash", description="Cash out before the crash")
    @defer_if_slow()
    async def crash(self, interaction: discord.Interaction, bet: str, cashout_at: float) -> None:
        if cashout_at < 1.01:
            raise ValueError("Cashout must be at least 1.01x")
        amount = parse_bet(bet)
        embed = gambling_embed("Crash", "📈 **1.00x**", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        mult = 1.0
        for _ in range(15):
            mult = round(mult + 0.15, 2)
            embed.description = f"📈 **{mult:.2f}x**"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.2)
        result = await self.bot.gambling.crash_cashout(interaction.user.id, interaction.guild_id, amount, cashout_at)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Crash", f"Crashed at **{result['crash_point']}x**\nYour cashout: **{result['cashout_at']}x**\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="plinko", description="Drop the plinko ball")
    @app_commands.choices(risk=[
        app_commands.Choice(name="Low", value="low"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="High", value="high"),
    ])
    @defer_if_slow()
    async def plinko(
        self,
        interaction: discord.Interaction,
        bet: str,
        risk: app_commands.Choice[str],
    ) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Plinko", "🔵 Dropping...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        await asyncio.sleep(0.8)
        result = await self.bot.gambling.plinko(interaction.user.id, interaction.guild_id, amount, risk.value)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Plinko", f"Slot **{result['slot']}** — **{result['multiplier']}x**\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="mines", description="Reveal tiles — avoid the mines")
    @defer_if_slow()
    async def mines(self, interaction: discord.Interaction, bet: str) -> None:
        amount = parse_bet(bet)
        await self.bot.gambling.place_bet(interaction.user.id, interaction.guild_id, amount)
        positions, seed = self.bot.gambling.generate_mines(5)
        view = MinesView(interaction.user.id, interaction.guild_id, amount, self.bot.gambling, positions, seed)
        embed = gambling_embed(
            "Mines",
            f"**Bet:** {format_money(amount)}\nReveal safe tiles and cash out!\n*5 mines hidden*",
            user=interaction.user,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed, view=view)

    @gamble.command(name="blackjack", description="Play blackjack")
    @defer_if_slow()
    async def blackjack(self, interaction: discord.Interaction, bet: str) -> None:
        amount = parse_bet(bet)
        await self.bot.gambling.place_bet(interaction.user.id, interaction.guild_id, amount)
        g = self.bot.gambling
        player = [g.deal_card(), g.deal_card()]
        dealer = [g.deal_card(), g.deal_card()]
        embed = gambling_embed(
            "Blackjack",
            f"**Your hand:** {player} ({g.blackjack_hand_value(player)})\n**Dealer:** {dealer[0]} + ?",
            user=interaction.user,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        await asyncio.sleep(0.5)
        while g.blackjack_hand_value(player) < 17:
            player.append(g.deal_card())
            embed.description = f"**Your hand:** {player} ({g.blackjack_hand_value(player)})\n**Dealer:** {dealer[0]} + ?"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)
        while g.blackjack_hand_value(dealer) < 17:
            dealer.append(g.deal_card())
        pv, dv = g.blackjack_hand_value(player), g.blackjack_hand_value(dealer)
        won = pv <= 21 and (dv > 21 or pv > dv)
        payout = (amount * Decimal("2")).quantize(Decimal("0.01")) if won else Decimal("0")
        if pv == 21 and len(player) == 2:
            payout = (amount * Decimal("2.5")).quantize(Decimal("0.01"))
            won = True
        await g.finalize_game(interaction.user.id, interaction.guild_id, GameType.BLACKJACK, amount, payout, won)
        fn = success_embed if won else error_embed
        embed = fn("Blackjack", f"**You:** {pv} | **Dealer:** {dv}\nPayout: {format_money(payout)}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="higherlower", description="Guess if the next card is higher or lower")
    @app_commands.choices(guess=[
        app_commands.Choice(name="Higher", value="higher"),
        app_commands.Choice(name="Lower", value="lower"),
    ])
    @defer_if_slow()
    async def higherlower(
        self,
        interaction: discord.Interaction,
        bet: str,
        guess: app_commands.Choice[str],
    ) -> None:
        amount = parse_bet(bet)
        result = await self.bot.gambling.higher_lower(
            interaction.user.id, interaction.guild_id, amount, guess.value
        )
        if result.get("push"):
            embed = gambling_embed("Higher/Lower — Push", f"{result['current']} → {result['next']}\nBet returned.", user=interaction.user, guild=interaction.guild)
        else:
            fn = success_embed if result["won"] else error_embed
            embed = fn("Higher/Lower", f"{result['current']} → {result['next']}\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @gamble.command(name="baccarat", description="Play baccarat")
    @app_commands.choices(bet_on=[
        app_commands.Choice(name="Player", value="player"),
        app_commands.Choice(name="Banker", value="banker"),
        app_commands.Choice(name="Tie", value="tie"),
    ])
    @defer_if_slow()
    async def baccarat(
        self,
        interaction: discord.Interaction,
        bet: str,
        bet_on: app_commands.Choice[str],
    ) -> None:
        amount = parse_bet(bet)
        result = await self.bot.gambling.baccarat(interaction.user.id, interaction.guild_id, amount, bet_on.value)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Baccarat", f"Player: **{result['player']}** | Banker: **{result['banker']}**\nWinner: **{result['winner']}**\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @gamble.command(name="tower", description="Climb the tower for multipliers")
    @defer_if_slow()
    async def tower(self, interaction: discord.Interaction, bet: str) -> None:
        amount = parse_bet(bet)
        embed = gambling_embed("Tower", "🏗️ Climbing...", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)
        msg = await interaction.original_response()
        result = await self.bot.gambling.tower(interaction.user.id, interaction.guild_id, amount)
        for f in range(result["floors_climbed"] + 1):
            embed.description = f"🏗️ Floor **{f}**"
            await msg.edit(embed=embed)
            await asyncio.sleep(0.4)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Tower", f"Climbed **{result['floors_climbed']}** floors ({result['multiplier']}x)\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await msg.edit(embed=embed)

    @gamble.command(name="duel", description="Dice duel against another player")
    @defer_if_slow()
    async def duel(self, interaction: discord.Interaction, user: discord.Member, bet: str) -> None:
        amount = parse_bet(bet)
        result = await self.bot.gambling.duel(interaction.user.id, interaction.guild_id, user.id, amount)
        fn = success_embed if result["won"] else error_embed
        embed = fn("Duel", f"You: **{result['your_roll']}** vs {user.display_name}: **{result['their_roll']}**\nPayout: {format_money(result['payout'])}", user=interaction.user, guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @gamble.command(name="games", description="List available casino games")
    async def games(self, interaction: discord.Interaction) -> None:
        games_list = (
            "Coinflip • Dice • Slots • Roulette • Blackjack • Higher/Lower • "
            "Baccarat • Limbo • Crash • Plinko • Mines • Tower • Duel"
        )
        embed = gambling_embed("Casino Games", games_list, user=interaction.user, guild=interaction.guild)
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GamblingCog(bot))
