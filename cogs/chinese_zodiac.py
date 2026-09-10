"""
Chinese zodiac: /chinesezodiac opens a modal for a birth date, computes the
animal + Wu Xing element (accounting for the Lunar New Year cutoff), and
assigns both as roles.
"""
from __future__ import annotations

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils import roles as role_utils
from utils.chinese import (
    get_chinese_zodiac, ANIMAL_EMOJI, ELEMENT_EMOJI, ANIMAL_BLURBS, ELEMENT_BLURBS,
)

log = logging.getLogger("fortunata.chinese_zodiac")

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]

ELEMENT_COLOR = {
    "Wood": 0x4C9A2A,
    "Fire": 0xE0402A,
    "Earth": 0x8B5A2B,
    "Metal": 0xB0B7C6,
    "Water": 0x2E6FCA,
}


def _parse_date(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError("Couldn't understand that date. Try YYYY-MM-DD, e.g. 1995-08-23.")


class ChineseZodiacModal(discord.ui.Modal, title="Find Your Chinese Zodiac"):
    birth_date = discord.ui.TextInput(
        label="Date of birth",
        placeholder="YYYY-MM-DD, e.g. 1995-08-23",
        required=True,
        max_length=32,
    )

    def __init__(self, cog: "ChineseZodiac"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            date_val = _parse_date(self.birth_date.value)
        except ValueError as exc:
            await interaction.response.send_message(f"⚠️ {exc}", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.assign_chinese_zodiac(interaction, date_val.date())


class ChineseZodiac(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(
        name="chinesezodiac",
        description="Find your Chinese zodiac animal and Five Element, and claim your roles.",
    )
    @app_commands.guild_only()
    async def chinesezodiac(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(ChineseZodiacModal(self))

    async def assign_chinese_zodiac(self, interaction: discord.Interaction, birth_date) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.followup.send("This only works inside the server.", ephemeral=True)
            return

        result = get_chinese_zodiac(birth_date)
        existing = await self.db.get_user(guild.id, member.id) or {}

        try:
            animal_role = await role_utils.get_or_create_role(
                guild, role_utils.chinese_animal_role_name(result.animal),
                color=discord.Color(0xC0392B), reason="Fortunata Chinese zodiac",
            )
            old_animal_role_name = (
                role_utils.chinese_animal_role_name(existing["chinese_animal"])
                if existing.get("chinese_animal") else None
            )
            await role_utils.replace_category_role(
                member, guild, old_animal_role_name, animal_role, reason="Fortunata Chinese zodiac"
            )

            element_role = await role_utils.get_or_create_role(
                guild, role_utils.chinese_element_role_name(result.element),
                color=discord.Color(ELEMENT_COLOR.get(result.element, 0x99AAB5)),
                reason="Fortunata Chinese zodiac element",
            )
            old_element_role_name = (
                role_utils.chinese_element_role_name(existing["chinese_element"])
                if existing.get("chinese_element") else None
            )
            await role_utils.replace_category_role(
                member, guild, old_element_role_name, element_role, reason="Fortunata Chinese zodiac element"
            )
        except role_utils.RoleError as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return

        await self.db.upsert_user(
            guild.id, member.id,
            chinese_animal=result.animal,
            chinese_element=result.element,
            chinese_lunar_year=result.lunar_year,
        )

        embed = discord.Embed(
            title=f"{ELEMENT_EMOJI[result.element]}{ANIMAL_EMOJI[result.animal]} {result.element} {result.animal}",
            description=(
                f"{ANIMAL_BLURBS[result.animal]}\n\n"
                f"**As a {result.element} sign:** {ELEMENT_BLURBS[result.element]}"
            ),
            color=ELEMENT_COLOR.get(result.element, 0x99AAB5),
        )
        embed.add_field(name="Lunar Year", value=str(result.lunar_year), inline=True)
        embed.set_footer(text="Roles for your animal and element have been added.")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(ChineseZodiac(bot))
