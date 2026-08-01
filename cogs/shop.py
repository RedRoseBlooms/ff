"""Shop and purchase commands with ticket workflow."""

from __future__ import annotations

from decimal import Decimal

import discord
from discord import app_commands
from discord.ext import commands

from services.shop_service import ShopService, TicketService
from utils.currency import format_money, parse_bet
from utils.embeds import economy_embed, success_embed, admin_embed, error_embed
from utils.interactions import defer_if_slow
from views.base import BaseView


class TicketControls(BaseView):
    def __init__(self, owner_id: int, ticket_service: TicketService) -> None:
        super().__init__(owner_id, timeout=None)
        self.ticket_service = ticket_service

    @discord.ui.button(label="Close Ticket", style=discord.ButtonStyle.danger)
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await self.ticket_service.close_ticket(interaction.channel_id, transcript="Closed via button")
        embed = admin_embed("Ticket Closed", "This ticket has been closed.")
        await interaction.response.send_message(embed=embed)
        await interaction.channel.delete(reason="Ticket closed")


class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.shop_service = ShopService(bot.db)
        self.ticket_service = TicketService(bot.db)

    shop = app_commands.Group(name="shop", description="Shop commands")

    @shop.command(name="browse", description="Browse the shop")
    @defer_if_slow()
    async def browse(self, interaction: discord.Interaction) -> None:
        items = await self.shop_service.shop.list_items(interaction.guild_id)
        if not items:
            await self.shop_service.shop.seed_defaults(interaction.guild_id)
            items = await self.shop_service.shop.list_items(interaction.guild_id)
        lines = [f"**#{i['id']}** {i['name']} — {format_money(i['price'])} ({i['category']})" for i in items]
        embed = economy_embed("Shop", "\n".join(lines) or "No items available.", guild=interaction.guild)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="buy", description="Purchase a shop item")
    @defer_if_slow()
    async def buy(self, interaction: discord.Interaction, item_id: int) -> None:
        purchase = await self.shop_service.purchase(interaction.user.id, interaction.guild_id, item_id)
        category_id = self.bot.config.ticket_category_id
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        if self.bot.config.staff_role_id:
            role = interaction.guild.get_role(self.bot.config.staff_role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
        channel = await interaction.guild.create_text_channel(
            name=f"ticket-{str(purchase['purchase_id'])[:8]}",
            category=discord.Object(id=category_id) if category_id else None,
            overwrites=overwrites,
        )
        await self.ticket_service.create_ticket_record(
            channel.id, interaction.user.id, interaction.guild_id, str(purchase["purchase_id"])
        )
        embed = success_embed(
            "Purchase Complete",
            f"**{purchase['item_name']}** — {format_money(purchase['price'])}\n"
            f"Purchase ID: `{purchase['purchase_id']}`\n"
            f"Ticket: {channel.mention}",
            user=interaction.user,
            guild=interaction.guild,
        )
        await interaction.followup.send(embed=embed)
        ticket_embed = economy_embed(
            "Delivery Ticket",
            f"**Customer:** {interaction.user.mention}\n"
            f"**Item:** {purchase['item_name']}\n"
            f"**Price:** {format_money(purchase['price'])}\n"
            f"**Purchase ID:** `{purchase['purchase_id']}`",
            guild=interaction.guild,
        )
        staff_ping = f"<@&{self.bot.config.staff_role_id}>" if self.bot.config.staff_role_id else "@staff"
        view = TicketControls(interaction.user.id, self.ticket_service)
        await channel.send(content=staff_ping, embed=ticket_embed, view=view)

    @shop.command(name="add", description="Add a shop item (Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    @defer_if_slow()
    async def add(
        self,
        interaction: discord.Interaction,
        name: str,
        price: str,
        description: str = "",
        category: str = "general",
    ) -> None:
        item = await self.shop_service.shop.add_item(
            interaction.guild_id, name, parse_bet(price), description, category
        )
        embed = admin_embed("Item Added", f"**{item['name']}** — {format_money(item['price'])} (#{item['id']})")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @shop.command(name="remove", description="Remove a shop item (Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    @defer_if_slow()
    async def remove(self, interaction: discord.Interaction, item_id: int) -> None:
        await self.shop_service.shop.remove_item(item_id)
        embed = admin_embed("Item Removed", f"Item #{item_id} deactivated.")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @shop.command(name="edit", description="Edit a shop item (Admin)")
    @app_commands.checks.has_permissions(administrator=True)
    @defer_if_slow()
    async def edit(
        self,
        interaction: discord.Interaction,
        item_id: int,
        name: str | None = None,
        price: str | None = None,
        description: str | None = None,
    ) -> None:
        fields = {}
        if name:
            fields["name"] = name
        if price:
            fields["price"] = parse_bet(price)
        if description:
            fields["description"] = description
        item = await self.shop_service.shop.edit_item(item_id, **fields)
        embed = admin_embed("Item Updated", f"**{item['name']}** — {format_money(item['price'])}")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ShopCog(bot))
