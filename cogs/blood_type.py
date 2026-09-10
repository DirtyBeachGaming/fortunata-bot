"""
Blood type astrology: /bloodtype shows a dropdown (A / B / AB / O), assigns
the matching role, and shows the personality blurb.
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils import roles as role_utils
from utils.blood import BLOOD_TYPES

log = logging.getLogger("fortunata.blood_type")


class BloodTypeSelect(discord.ui.Select):
    def __init__(self, cog: "BloodTypeCog"):
        options = [
            discord.SelectOption(label=bt.label, value=bt.key, emoji=bt.emoji)
            for bt in BLOOD_TYPES.values()
        ]
        super().__init__(
            placeholder="Select your blood type…",
            min_values=1, max_values=1, options=options,
        )
        self.cog = cog

    async def callback(self, interaction: discord.Interaction):
        await self.cog.assign_blood_type(interaction, self.values[0])


class BloodTypeView(discord.ui.View):
    def __init__(self, cog: "BloodTypeCog"):
        super().__init__(timeout=180)
        self.add_item(BloodTypeSelect(cog))


class BloodTypeCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(
        name="bloodtype",
        description="Find your blood type personality (A/B/AB/O) and claim your role.",
    )
    @app_commands.guild_only()
    async def bloodtype(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            "🩸 Blood type astrology (*ketsuekigata*) — pick yours:",
            view=BloodTypeView(self),
            ephemeral=True,
        )

    async def assign_blood_type(self, interaction: discord.Interaction, key: str) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.response.send_message("This only works inside the server.", ephemeral=True)
            return

        blood = BLOOD_TYPES[key]
        existing = await self.db.get_user(guild.id, member.id) or {}

        await interaction.response.defer(ephemeral=True)

        try:
            role = await role_utils.get_or_create_role(
                guild, role_utils.blood_role_name(blood),
                color=discord.Color(blood.color), reason="Fortunata blood type",
            )
            old_role_name = (
                role_utils.blood_role_name(BLOOD_TYPES[existing["blood_type"]])
                if existing.get("blood_type") in BLOOD_TYPES else None
            )
            await role_utils.replace_category_role(
                member, guild, old_role_name, role, reason="Fortunata blood type"
            )
        except role_utils.RoleError as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return

        await self.db.upsert_user(guild.id, member.id, blood_type=blood.key)

        embed = discord.Embed(
            title=f"{blood.emoji} {blood.label}",
            description=blood.blurb,
            color=blood.color,
        )
        embed.add_field(name="Strengths", value=blood.strengths, inline=False)
        embed.add_field(name="Watch for", value=blood.watch_for, inline=False)
        embed.set_footer(text="Just for fun — not a medical or scientific claim. 🍷")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BloodTypeCog(bot))
