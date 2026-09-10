"""
Full natal chart: /placements opens a modal asking for birth date, time,
and location, then computes and role-assigns every major placement
(Sun through Pluto, plus the Ascendant/Rising sign).
"""
from __future__ import annotations

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from utils import roles as role_utils
from utils.astrology import get_sign
from utils.chart import compute_natal_chart, GeocodeError, ChartError, PLANETS, ASCENDANT_LABEL

log = logging.getLogger("fortunata.placements")

DATE_FORMATS = ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"]

# db column that stores each placement key's sign
_DB_COLUMN = {
    "sun": "sun_sign",
    "moon": "moon_sign",
    "mercury": "mercury_sign",
    "venus": "venus_sign",
    "mars": "mars_sign",
    "jupiter": "jupiter_sign",
    "saturn": "saturn_sign",
    "uranus": "uranus_sign",
    "neptune": "neptune_sign",
    "pluto": "pluto_sign",
    "ascendant": "ascendant_sign",
}


def _parse_date(raw: str) -> datetime:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    raise ValueError(
        "Couldn't understand that date. Try YYYY-MM-DD, e.g. 1995-08-23."
    )


def _parse_time(raw: str) -> tuple[int, int, bool]:
    """Returns (hour, minute, is_approximate)."""
    raw = raw.strip()
    if not raw:
        return 12, 0, True
    for fmt in ("%H:%M", "%I:%M %p", "%I:%M%p"):
        try:
            t = datetime.strptime(raw, fmt)
            return t.hour, t.minute, False
        except ValueError:
            continue
    raise ValueError(
        "Couldn't understand that time. Try 24-hour HH:MM (e.g. 14:30), "
        "or leave it blank if you don't know."
    )


class PlacementsModal(discord.ui.Modal, title="Find Your Full Birth Chart"):
    birth_date = discord.ui.TextInput(
        label="Date of birth",
        placeholder="YYYY-MM-DD, e.g. 1995-08-23",
        required=True,
        max_length=32,
    )
    birth_time = discord.ui.TextInput(
        label="Time of birth (24h, leave blank if unknown)",
        placeholder="HH:MM, e.g. 14:30",
        required=False,
        max_length=16,
    )
    birth_location = discord.ui.TextInput(
        label="Birth city (and country)",
        placeholder="e.g. Naples, Italy",
        required=True,
        max_length=100,
    )

    def __init__(self, cog: "Placements"):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction) -> None:
        try:
            date_val = _parse_date(self.birth_date.value)
            hour, minute, approximate = _parse_time(self.birth_time.value)
        except ValueError as exc:
            await interaction.response.send_message(f"⚠️ {exc}", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        await self.cog.run_chart(
            interaction,
            name=str(interaction.user),
            year=date_val.year,
            month=date_val.month,
            day=date_val.day,
            hour=hour,
            minute=minute,
            approximate_time=approximate,
            location=str(self.birth_location.value),
        )


class Placements(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(
        name="placements",
        description="Find your full birth chart (Sun through Pluto + Rising) and claim your placement roles.",
    )
    @app_commands.guild_only()
    async def placements(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(PlacementsModal(self))

    async def run_chart(
        self,
        interaction: discord.Interaction,
        *,
        name: str,
        year: int,
        month: int,
        day: int,
        hour: int,
        minute: int,
        approximate_time: bool,
        location: str,
    ) -> None:
        guild = interaction.guild
        member = interaction.user
        if guild is None or not isinstance(member, discord.Member):
            await interaction.followup.send("This only works inside the server.", ephemeral=True)
            return

        try:
            chart = await compute_natal_chart(
                name=name, year=year, month=month, day=day,
                hour=hour, minute=minute, location=location,
            )
        except (GeocodeError, ChartError) as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return
        except Exception:
            log.exception("Unexpected error computing chart for %s", member)
            await interaction.followup.send(
                "⚠️ Something went wrong computing your chart. Please try again shortly.",
                ephemeral=True,
            )
            return

        existing = await self.db.get_user(guild.id, member.id) or {}
        config = await self.db.get_guild_config(guild.id) or {}

        embed = discord.Embed(
            title=f"🔮 {member.display_name}'s Natal Chart",
            description=(
                f"Born {year:04d}-{month:02d}-{day:02d}"
                + ("" if approximate_time else f" at {hour:02d}:{minute:02d}")
                + f"\n📍 {chart.location_label}"
                + ("\n*Time unknown — using noon, so Rising/Moon may be a little off.*" if approximate_time else "")
            ),
            color=chart.placements["sun"].color,
        )

        db_fields: dict = {
            "verified": 1,
            "birth_year": year, "birth_month": month, "birth_day": day,
            "birth_hour": hour, "birth_minute": minute,
            "birth_location": chart.location_label,
            "birth_lat": chart.lat, "birth_lon": chart.lon, "birth_tz": chart.tz_str,
        }

        try:
            for planet_key, sign in chart.placements.items():
                role_name = role_utils.planet_role_name(planet_key, sign)
                role = await role_utils.get_or_create_role(
                    guild, role_name, color=discord.Color(sign.color),
                    reason="Fortunata placement chart",
                )
                old_role_name = None
                old_sign_key = existing.get(_DB_COLUMN[planet_key])
                if old_sign_key:
                    old_sign = get_sign(old_sign_key)
                    if old_sign:
                        old_role_name = role_utils.planet_role_name(planet_key, old_sign)
                await role_utils.replace_category_role(
                    member, guild, old_role_name, role, reason="Fortunata placement chart"
                )
                db_fields[_DB_COLUMN[planet_key]] = sign.key

            if config.get("verified_role_id"):
                verified_role = guild.get_role(config["verified_role_id"])
                if verified_role:
                    await role_utils.assign_role(member, verified_role, reason="Fortunata full chart")
            if config.get("unverified_role_id"):
                unverified_role = guild.get_role(config["unverified_role_id"])
                if unverified_role:
                    await role_utils.remove_role(member, unverified_role, reason="Fortunata full chart")
        except role_utils.RoleError as exc:
            await interaction.followup.send(f"⚠️ {exc}", ephemeral=True)
            return

        await self.db.upsert_user(guild.id, member.id, **db_fields)

        for planet_key, label, emoji in PLANETS:
            sign = chart.placements[planet_key]
            embed.add_field(name=f"{emoji} {label}", value=f"{sign.symbol} {sign.name}", inline=True)
        asc_label, asc_emoji = ASCENDANT_LABEL
        asc_sign = chart.placements["ascendant"]
        embed.add_field(name=f"{asc_emoji} {asc_label}", value=f"{asc_sign.symbol} {asc_sign.name}", inline=True)

        embed.set_footer(text="Roles for every placement above have been added. Use /profile any time to see this again.")
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Placements(bot))
