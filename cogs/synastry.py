"""
/synastry — a real, non-joke compatibility reading.

Unlike /compatibility (a running gag that always points back to
Trimalchio), this recalculates both members' exact chart degrees from the
birth data they already gave /placements, and checks the ten cross-chart
pairings astrologers actually lean on for romantic/relationship
compatibility (Sun, Moon, Venus, Mars, Ascendant) for real aspects
(conjunction/sextile/square/trine/opposition), then blends the results
into one score. Deterministic — the same two charts always produce the
same reading, no randomness involved.

Requires both members to have already run /placements (that's where their
exact birth date/time/location gets saved).
"""
from __future__ import annotations

import logging

import discord
from discord import app_commands
from discord.ext import commands

from utils.chart import compute_exact_positions, ChartError, PLANETS

log = logging.getLogger("fortunata.synastry")

# label -> kerykeion attr, for the handful of points synastry cares about
_PLANET_LABELS = {attr: label for attr, label, _emoji in PLANETS}
_PLANET_LABELS["ascendant"] = "Ascendant"
_PLANET_EMOJI = {attr: emoji for attr, _label, emoji in PLANETS}
_PLANET_EMOJI["ascendant"] = "⬆️"

# Major aspects: (name, target angle, orb allowed, emoji, score out of 10)
_ASPECTS: list[tuple[str, float, float, str, float]] = [
    ("Conjunction", 0, 8, "🔗", 9.0),
    ("Sextile", 60, 6, "✨", 7.5),
    ("Square", 90, 7, "⚔️", 2.5),
    ("Trine", 120, 8, "💫", 10.0),
    ("Opposition", 180, 8, "🌓", 5.0),
]

_ASPECT_TONE = {
    "Conjunction": "fuse into one shared signal — intense and unmistakable, impossible for either of you to ignore.",
    "Trine": "flow together with almost no friction — a natural, easy harmony.",
    "Sextile": "open a door for each other, one that's only worth anything if you both actually walk through it.",
    "Opposition": "pull toward each other like two poles of the same magnet — magnetic, but never fully settled.",
    "Square": "rub against each other — real friction, the kind that forces growth whether either of you wants it or not.",
}
_NO_ASPECT_SCORE = 5.0
_NO_ASPECT_TEXT = "don't make direct contact — not a strain, not a spark, just quiet."

# The ten cross-chart pairings checked, in (planet_a, planet_b, headline) form.
_PAIRS: list[tuple[str, str, str]] = [
    ("sun", "sun", "Core identity"),
    ("moon", "moon", "Emotional wavelength"),
    ("sun", "moon", "{a}'s sense of self meets {b}'s emotional instincts"),
    ("moon", "sun", "{a}'s emotional instincts meet {b}'s sense of self"),
    ("venus", "venus", "Love language"),
    ("mars", "mars", "Drive and desire"),
    ("venus", "mars", "{a}'s love language meets {b}'s drive"),
    ("mars", "venus", "{a}'s drive meets {b}'s love language"),
    ("sun", "ascendant", "{a}'s core self meets {b}'s first impression"),
    ("ascendant", "sun", "{a}'s first impression meets {b}'s core self"),
]


def _closest_aspect(deg_a: float, deg_b: float) -> tuple[str, str, float] | None:
    """Returns (aspect_name, emoji, score) for the closest major aspect
    between two absolute zodiac degrees, or None if nothing's in orb."""
    diff = abs(deg_a - deg_b) % 360
    if diff > 180:
        diff = 360 - diff

    best: tuple[str, str, float, float] | None = None  # name, emoji, score, delta
    for name, angle, orb, emoji, score in _ASPECTS:
        delta = abs(diff - angle)
        if delta <= orb and (best is None or delta < best[3]):
            best = (name, emoji, score, delta)
    if best is None:
        return None
    name, emoji, score, _delta = best
    return name, emoji, score


class Synastry(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = bot.db  # type: ignore[attr-defined]

    @app_commands.command(
        name="synastry",
        description="A real chart-based compatibility reading (defaults to you).",
    )
    @app_commands.describe(
        member="Who to check synastry with",
        as_member="Check as this member instead of yourself (optional)",
    )
    @app_commands.guild_only()
    async def synastry(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        as_member: discord.Member | None = None,
    ) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "This only works inside the server.", ephemeral=True
            )
            return

        person_a = as_member or interaction.user
        person_b = member

        if person_a.id == person_b.id:
            await interaction.response.send_message(
                "You can't run synastry between someone and themselves — "
                "pick two different people.",
                ephemeral=True,
            )
            return

        data_a = await self.db.get_user(guild.id, person_a.id) or {}
        data_b = await self.db.get_user(guild.id, person_b.id) or {}

        missing = []
        for person, data in ((person_a, data_a), (person_b, data_b)):
            if data.get("birth_lat") is None or data.get("birth_lon") is None or not data.get("birth_tz"):
                missing.append(person.mention)
        if missing:
            await interaction.response.send_message(
                f"⚠️ {', '.join(missing)} still need{'s' if len(missing) == 1 else ''} to run "
                f"`/placements` first — synastry needs a full birth chart on file, not just a Sun sign.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(thinking=True)

        try:
            exact_a = await compute_exact_positions(
                name=person_a.display_name,
                year=data_a["birth_year"], month=data_a["birth_month"], day=data_a["birth_day"],
                hour=data_a["birth_hour"], minute=data_a["birth_minute"],
                lat=data_a["birth_lat"], lon=data_a["birth_lon"], tz_str=data_a["birth_tz"],
            )
            exact_b = await compute_exact_positions(
                name=person_b.display_name,
                year=data_b["birth_year"], month=data_b["birth_month"], day=data_b["birth_day"],
                hour=data_b["birth_hour"], minute=data_b["birth_minute"],
                lat=data_b["birth_lat"], lon=data_b["birth_lon"], tz_str=data_b["birth_tz"],
            )
        except ChartError as exc:
            await interaction.followup.send(f"⚠️ {exc}")
            return
        except Exception:
            log.exception("Unexpected error computing synastry for %s / %s", person_a, person_b)
            await interaction.followup.send(
                "⚠️ Something went wrong recalculating those charts. Please try again shortly."
            )
            return

        fields: list[tuple[str, str]] = []
        total = 0.0
        for planet_a, planet_b, headline_tmpl in _PAIRS:
            deg_a = exact_a.degrees[planet_a]
            deg_b = exact_b.degrees[planet_b]
            sign_a = exact_a.signs[planet_a]
            sign_b = exact_b.signs[planet_b]

            headline = headline_tmpl.format(a=person_a.display_name, b=person_b.display_name)
            result = _closest_aspect(deg_a, deg_b)

            emoji_a = _PLANET_EMOJI[planet_a]
            emoji_b = _PLANET_EMOJI[planet_b]
            label_a = _PLANET_LABELS[planet_a]
            label_b = _PLANET_LABELS[planet_b]

            if result is not None:
                aspect_name, aspect_emoji, score = result
                tone = _ASPECT_TONE[aspect_name]
                value = (
                    f"{emoji_a} {sign_a.symbol} {label_a} ({person_a.display_name}) "
                    f"{aspect_emoji} **{aspect_name}** {aspect_emoji} "
                    f"{emoji_b} {sign_b.symbol} {label_b} ({person_b.display_name})\n"
                    f"These two {tone}"
                )
            else:
                score = _NO_ASPECT_SCORE
                value = (
                    f"{emoji_a} {sign_a.symbol} {label_a} ({person_a.display_name}) and "
                    f"{emoji_b} {sign_b.symbol} {label_b} ({person_b.display_name}) "
                    f"{_NO_ASPECT_TEXT}"
                )

            total += score
            fields.append((f"{headline}", value))

        overall = round((total / (len(_PAIRS) * 10)) * 100)
        overall = max(0, min(100, overall))

        if overall >= 80:
            verdict = "Exceptionally aligned — this is a rare amount of real astrological agreement."
        elif overall >= 62:
            verdict = "Strong compatibility, with plenty working in your favor."
        elif overall >= 42:
            verdict = "Workable, with real friction to navigate — not fated, not doomed."
        else:
            verdict = "A genuine challenge on paper. Not impossible, but the charts aren't making it easy."

        embed = discord.Embed(
            title="🔮 Synastry Reading",
            description=(
                f"{person_a.mention} × {person_b.mention} — calculated from each of "
                f"your saved birth charts, not a bit.\n\n"
                f"**Overall: {overall}%** — {verdict}"
            ),
            color=0x8E44AD,
        )
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(
            text="🍇 Trimalchio's Dinner Party — real aspects, exact degrees, no randomness."
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(Synastry(bot))
