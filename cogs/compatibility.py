"""
/compatibility — a running gag, not a real astrology feature. Whoever you
check against, the punchline is always the same: your true match was
Trimalchio all along, and Trimalchio's own true match is a running joke
of its own.
"""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.astrology import get_sign

# Flavor text varies each time; the two "facts" below never do.
TWIST_LINES = [
    "But halfway through the second course, the truth becomes impossible to ignore.",
    "And yet, as the wine keeps coming, something else becomes clear.",
    "Still, by the time the roasted boar arrives, the stars have other plans.",
    "But Trimalchio, reclining at the head of the table, catches your eye — and everything changes.",
    "The astrolabe on the table spins once, twice, and lands somewhere neither of you expected.",
]

CLOSING_LINE = (
    "🍷 For the record: Trimalchio himself is most compatible with "
    "*uxor Trimalchionis*, Gwendalini."
)


class Compatibility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(
        name="compatibility",
        description="Check your compatibility with another member.",
    )
    @app_commands.describe(member="Who to check compatibility with")
    @app_commands.guild_only()
    async def compatibility(self, interaction: discord.Interaction, member: discord.Member) -> None:
        guild = interaction.guild
        asker = interaction.user
        if guild is None:
            await interaction.response.send_message(
                "This only works inside the server.", ephemeral=True
            )
            return

        asker_data = await self.db.get_user(guild.id, asker.id) or {}
        target_data = await self.db.get_user(guild.id, member.id) or {}
        asker_sign = get_sign(asker_data.get("sun_sign")) if asker_data.get("sun_sign") else None
        target_sign = get_sign(target_data.get("sun_sign")) if target_data.get("sun_sign") else None

        score = random.randint(4, 61)

        if asker_sign and target_sign:
            reading_line = (
                f"{asker_sign.symbol} {asker_sign.name} and {target_sign.symbol} {target_sign.name} "
                f"— **{score}%** compatible."
            )
        else:
            reading_line = f"You and {member.mention} — **{score}%** compatible."

        twist = random.choice(TWIST_LINES)

        description = (
            f"{reading_line}\n\n"
            f"{twist} Your true match was here all along.\n\n"
            f"**{asker.mention} + Trimalchio: 💯% compatible.**\n\n"
            f"{CLOSING_LINE}"
        )

        embed = discord.Embed(
            title="💘 A Compatibility Reading",
            description=description,
            color=0x8E44AD,
        )
        embed.set_footer(text="🍇 Trimalchio's Dinner Party")
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Compatibility(bot))
