"""
/compatibility — mostly a running gag, but dressed up as a real reading.

It actually reasons through elemental and modality compatibility using
each person's Sun sign (when they have one on file) before landing on the
same punchline every time: your true match was Trimalchio all along.

Two accounts are hardcoded as the one true exception — whichever order
they check each other in, they're simply told they're soulmates, no
mechanics, no joke.
"""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.astrology import get_sign, ZodiacSign

# The one real pairing. Checking compatibility between these two (in either
# direction) skips the joke machinery entirely.
SOULMATE_PAIR = {1439520700690862102, 1250948992582553661}

# Traditional elemental compatibility, keyed by the unordered pair of
# elements. (description, (low, high) percentage range)
ELEMENT_COMPAT: dict[frozenset, tuple[str, tuple[int, int]]] = {
    frozenset({"Fire"}): (
        "Two Fire signs recognize the spark in each other instantly — thrilling, "
        "but two flames sharing one hearth tend to argue about whose fire burns brighter.",
        (45, 75),
    ),
    frozenset({"Fire", "Air"}): (
        "Air feeds Fire. This is one of the classic easy pairings — one brings the "
        "spark, the other brings the oxygen, and neither has to try very hard.",
        (60, 92),
    ),
    frozenset({"Fire", "Earth"}): (
        "Fire scorches Earth, and Earth smothers Fire. Workable with patience, but the "
        "natural instinct of each sign undoes what the other is trying to build.",
        (15, 42),
    ),
    frozenset({"Fire", "Water"}): (
        "Fire meets Water and one of them loses. Sometimes that reads as passion, "
        "sometimes as steam evaporating before anything can settle.",
        (18, 48),
    ),
    frozenset({"Earth"}): (
        "Two Earth signs build something that lasts — dependable, a little "
        "predictable, and neither one in a hurry to shake things up.",
        (48, 74),
    ),
    frozenset({"Earth", "Water"}): (
        "Water nourishes Earth. This is the other classic easy pairing — one gives "
        "shape, the other gives depth, and both come away better for it.",
        (58, 90),
    ),
    frozenset({"Earth", "Air"}): (
        "Air has no interest in staying still long enough for Earth to take root. "
        "Great conversation, very little follow-through.",
        (20, 45),
    ),
    frozenset({"Air"}): (
        "Two Air signs talk endlessly and understand each other perfectly — right up "
        "until someone has to actually commit to something.",
        (50, 78),
    ),
    frozenset({"Air", "Water"}): (
        "Air unsettles Water's stillness, and Water's moods are, frankly, too much "
        "weather for Air to plan around.",
        (20, 48),
    ),
    frozenset({"Water"}): (
        "Two Water signs recognize the tide in each other — deeply intuitive, deeply "
        "felt, and occasionally a lot to hold at once.",
        (52, 80),
    ),
}

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


def _quality_note(sign_a: ZodiacSign, sign_b: ZodiacSign) -> str:
    if sign_a.quality == sign_b.quality:
        return (
            f"Both {sign_a.quality.lower()} signs — which means neither one is "
            f"built to back down first."
        )
    return (
        f"A {sign_a.quality} sign meeting a {sign_b.quality} one — different "
        f"instincts for who leads, who holds steady, and who goes along with it."
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

        # The one real exception, either direction. Always names them the
        # same way — Trimalchio first, Gwendalini second — no matter who
        # actually ran the command or who they picked as `member`.
        if {asker.id, member.id} == SOULMATE_PAIR:
            people = {asker.id: asker, member.id: member}
            trimalchio_user = people[1439520700690862102]
            gwendalini_user = people[1250948992582553661]

            embed = discord.Embed(
                title="💞 Destiny, Not Chance",
                description=(
                    f"{trimalchio_user.mention} (Trimalchio) and "
                    f"{gwendalini_user.mention} (Gwendalini) — there's no reading "
                    f"to give here, no elements to weigh against each other. This "
                    f"one was written into the fresco before either of you "
                    f"arrived.\n\n"
                    f"**💯% — soul mates.**"
                ),
                color=0xE8A0C4,
            )
            embed.set_footer(text="🍇 Trimalchio's Dinner Party")
            await interaction.response.send_message(embed=embed)
            return

        asker_data = await self.db.get_user(guild.id, asker.id) or {}
        target_data = await self.db.get_user(guild.id, member.id) or {}
        asker_sign = get_sign(asker_data.get("sun_sign")) if asker_data.get("sun_sign") else None
        target_sign = get_sign(target_data.get("sun_sign")) if target_data.get("sun_sign") else None

        if asker_sign and target_sign:
            key = frozenset({asker_sign.element, target_sign.element})
            element_desc, score_range = ELEMENT_COMPAT[key]
            score = random.randint(*score_range)
            reading = (
                f"{asker_sign.symbol} **{asker_sign.name}** ({asker_sign.element}) meets "
                f"{target_sign.symbol} **{target_sign.name}** ({target_sign.element}).\n\n"
                f"{element_desc}\n\n"
                f"{_quality_note(asker_sign, target_sign)}\n\n"
                f"**Compatibility: {score}%**"
            )
        else:
            score = random.randint(4, 61)
            missing = asker.mention if not asker_sign else member.mention
            reading = (
                f"You and {member.mention} — **{score}%** compatible.\n\n"
                f"*(The reading would run deeper if {missing} had claimed a Sun sign — "
                f"try `/placements` or the verification panel.)*"
            )

        twist = random.choice(TWIST_LINES)

        description = (
            f"{reading}\n\n"
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
