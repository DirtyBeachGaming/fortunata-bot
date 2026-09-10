"""
Verification gate: new arrivals to Trimalchio's Dinner Party must claim a
Sun sign before they can see the rest of the banquet.

Two paths, both ending in the same place:
  1. They already know their sign -> click its button directly.
  2. They don't -> click "Find My Sign", then pick the date range that
     contains their birthday from a dropdown.
"""
from __future__ import annotations

import logging

import discord
from discord.ext import commands

from utils.astrology import ZODIAC_SIGNS, SIGN_ORDER, date_range_label, get_sign
from utils import roles as role_utils

log = logging.getLogger("fortunata.verification")

WELCOME_TITLE = "🍷 You've arrived at Trimalchio's table."
FIND_SIGN_CUSTOM_ID = "fortunata:verify:find"


def _sign_button_row(index: int) -> int:
    # 12 sign buttons across 3 rows of 4, "find my sign" gets its own row
    return index // 4


class FindSignSelect(discord.ui.Select):
    def __init__(self, cog: "Verification"):
        options = []
        for key in SIGN_ORDER:
            sign = ZODIAC_SIGNS[key]
            options.append(
                discord.SelectOption(
                    label=f"{sign.name}  ({date_range_label(sign)})",
                    value=sign.key,
                    emoji=sign.emoji,
                )
            )
        super().__init__(
            placeholder="Select the range your birthday falls in…",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="fortunata:verify:find:select",
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        sign_key = self.values[0]
        await self.cog.verify_member(interaction, sign_key)


class FindSignView(discord.ui.View):
    def __init__(self, cog: "Verification"):
        super().__init__(timeout=180)
        self.add_item(FindSignSelect(cog))


class VerificationPanelView(discord.ui.View):
    """The persistent panel posted in the verification channel."""

    def __init__(self, cog: "Verification"):
        super().__init__(timeout=None)
        for i, key in enumerate(SIGN_ORDER):
            sign = ZODIAC_SIGNS[key]
            button: discord.ui.Button = discord.ui.Button(
                label=sign.name,
                emoji=sign.emoji,
                style=discord.ButtonStyle.secondary,
                custom_id=f"fortunata:verify:{sign.key}",
                row=_sign_button_row(i),
            )

            async def _callback(interaction: discord.Interaction, _key=sign.key):
                await cog.verify_member(interaction, _key)

            button.callback = _callback
            self.add_item(button)

        find_button: discord.ui.Button = discord.ui.Button(
            label="Find My Sign",
            emoji="🔍",
            style=discord.ButtonStyle.primary,
            custom_id=FIND_SIGN_CUSTOM_ID,
            row=3,
        )

        async def _find_callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                "Pick the date range your birthday falls in:",
                view=FindSignView(cog),
                ephemeral=True,
            )

        find_button.callback = _find_callback
        self.add_item(find_button)


class Verification(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    async def cog_load(self) -> None:
        # Re-register the persistent view so buttons keep working after a
        # bot restart (custom_ids must match exactly).
        self.bot.add_view(VerificationPanelView(self))

    # ------------------------------------------------------------- events

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.bot:
            return
        config = await self.db.get_guild_config(member.guild.id)
        if not config or not config.get("unverified_role_id"):
            return
        role = member.guild.get_role(config["unverified_role_id"])
        if role is None:
            return
        try:
            await member.add_roles(role, reason="Fortunata: new arrival, pending verification")
        except discord.HTTPException:
            log.warning("Couldn't add unverified role to %s in %s", member, member.guild)

        channel_id = config.get("verification_channel_id")
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            jump = f" {channel.mention}" if isinstance(channel, discord.abc.GuildChannel) else ""
        else:
            jump = ""
        try:
            await member.send(
                f"🍷 Welcome to **{member.guild.name}** — Trimalchio's Dinner Party. "
                f"Head to{jump or ' the verification channel'} and claim your Sun "
                f"sign to be let in to the feast."
            )
        except discord.Forbidden:
            pass  # DMs closed, no big deal

    # ----------------------------------------------------------------- core

    async def verify_member(self, interaction: discord.Interaction, sign_key: str) -> None:
        sign = get_sign(sign_key)
        if sign is None:
            await interaction.response.send_message("Something went wrong — unknown sign.", ephemeral=True)
            return
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message(
                "Verification only works inside the server.", ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)

        config = await self.db.get_guild_config(guild.id) or {}

        try:
            sun_role = await role_utils.get_or_create_role(
                guild,
                role_utils.sun_role_name(sign),
                color=discord.Color(sign.color),
                reason="Fortunata sun sign verification",
            )

            existing = await self.db.get_user(guild.id, member.id)
            old_role_name = (
                role_utils.sun_role_name(get_sign(existing["sun_sign"]))
                if existing and existing.get("sun_sign")
                else None
            )
            await role_utils.replace_category_role(
                member, guild, old_role_name, sun_role,
                reason="Fortunata sun sign verification",
            )

            if config.get("verified_role_id"):
                verified_role = guild.get_role(config["verified_role_id"])
                if verified_role:
                    await role_utils.assign_role(member, verified_role, reason="Fortunata verification")
            if config.get("unverified_role_id"):
                unverified_role = guild.get_role(config["unverified_role_id"])
                if unverified_role:
                    await role_utils.remove_role(member, unverified_role, reason="Fortunata verification")
        except role_utils.RoleError as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return

        await self.db.upsert_user(guild.id, member.id, verified=1, sun_sign=sign.key)

        embed = discord.Embed(
            title=f"{sign.emoji} You are {sign.name} {sign.symbol}",
            description=sign.blurb,
            color=sign.color,
        )
        embed.add_field(name="Dates", value=date_range_label(sign), inline=True)
        embed.add_field(name="Element", value=sign.element, inline=True)
        embed.add_field(name="Ruled by", value=sign.ruling_planet, inline=True)
        embed.set_footer(text="You're in. Enjoy the banquet. 🍇")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Verification(bot))
