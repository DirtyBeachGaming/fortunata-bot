"""
/profile — a shareable summary card of everything Fortunata knows about a
member: sun/moon/rising + full chart if they've run it, Chinese zodiac,
and blood type. Exact birth time/location are deliberately left out here
(they're only ever shown back to the member privately by /placements) —
this command is meant to be safe to run on other members.
"""
from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from utils.astrology import get_sign
from utils.chinese import ANIMAL_EMOJI, ELEMENT_EMOJI as CN_ELEMENT_EMOJI
from utils.blood import BLOOD_TYPES
from utils.chart import PLANETS, ASCENDANT_LABEL

NOT_SET = "*unset*"


class Profile(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(name="profile", description="Show your (or someone else's) Fortunata astrology profile.")
    @app_commands.describe(member="Whose profile to show (defaults to you)")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None) -> None:
        guild = interaction.guild
        target = member or interaction.user
        if guild is None or not isinstance(target, discord.Member):
            await interaction.response.send_message("This only works inside the server.", ephemeral=True)
            return

        data = await self.db.get_user(guild.id, target.id)
        if not data:
            await interaction.response.send_message(
                f"No astrology data on file for {target.mention} yet. "
                f"Try `/placements`, `/chinesezodiac`, or `/bloodtype`.",
                ephemeral=True,
            )
            return

        sun = get_sign(data.get("sun_sign")) if data.get("sun_sign") else None
        color = sun.color if sun else 0x8E44AD

        embed = discord.Embed(
            title=f"🔮 {target.display_name}'s Fortunata Profile",
            color=color,
        )
        embed.set_thumbnail(url=target.display_avatar.url)

        chart_lines = []
        for attr, label, emoji in PLANETS:
            sign = get_sign(data.get(f"{attr}_sign")) if data.get(f"{attr}_sign") else None
            chart_lines.append(f"{emoji} **{label}:** {sign.symbol + ' ' + sign.name if sign else NOT_SET}")
        asc_label, asc_emoji = ASCENDANT_LABEL
        asc = get_sign(data.get("ascendant_sign")) if data.get("ascendant_sign") else None
        chart_lines.append(f"{asc_emoji} **{asc_label}:** {asc.symbol + ' ' + asc.name if asc else NOT_SET}")
        embed.add_field(name="Western Chart", value="\n".join(chart_lines), inline=False)

        animal = data.get("chinese_animal")
        element = data.get("chinese_element")
        if animal or element:
            cn = f"{CN_ELEMENT_EMOJI.get(element, '')}{ANIMAL_EMOJI.get(animal, '')} {element or ''} {animal or ''}".strip()
        else:
            cn = NOT_SET
        embed.add_field(name="🀄 Chinese Zodiac", value=cn, inline=True)

        blood_key = data.get("blood_type")
        blood = BLOOD_TYPES.get(blood_key) if blood_key else None
        embed.add_field(name="🩸 Blood Type", value=f"{blood.emoji} {blood.label}" if blood else NOT_SET, inline=True)

        embed.set_footer(text="🍷 Trimalchio's Dinner Party")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Profile(bot))
