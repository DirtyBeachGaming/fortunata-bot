"""
/compatibility — mostly a running gag, but dressed up as a real reading.

It reasons through Sun-sign element/modality, Chinese zodiac animal +
Wu Xing element, and blood type — whichever of those either person has on
file — blending them into one combined score, before landing on the same
punchline every time: your true match was Trimalchio all along.

Two accounts are hardcoded as the one true exception — whichever order
they check each other in, they're simply told they're soulmates, no
mechanics, no joke.

By default the reading is you vs. whoever you pick. Pass `as_member` to
instead check compatibility between two OTHER members, with yourself out
of it entirely.
"""
from __future__ import annotations

import random

import discord
from discord import app_commands
from discord.ext import commands

from utils.astrology import get_sign, ZodiacSign
from utils.chinese import ANIMAL_EMOJI
from utils.blood import BLOOD_TYPES

# The one real pairing. Checking compatibility between these two (in either
# direction) skips the joke machinery entirely.
TRIMALCHIO_ID = 1439520700690862102
GWENDALINI_ID = 1250948992582553661
SOULMATE_PAIR = {TRIMALCHIO_ID, GWENDALINI_ID}

# Alternate finales used in place of "{person_a} + Trimalchio: 100% compatible"
# for the one case where that line doesn't make sense: Trimalchio himself
# being the subject of the reading, checked against someone who isn't
# Gwendalini (that pairing is already handled above and never reaches this
# point).
TRIMALCHIO_ASKER_LINES = [
    "**Verdict: charming, but no — Trimalchio's heart was already spoken for long before {target} sat down.**",
    "**Verdict: {target} is delightful company, but Trimalchio's true match is already reclining at this table.**",
    "**Verdict: a pleasant reading, nothing more — Trimalchio's stars were settled on someone else long ago.**",
]

# --------------------------------------------------------------- sun sign

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


def _sun_component(sign_a: ZodiacSign, sign_b: ZodiacSign) -> tuple[int, str]:
    key = frozenset({sign_a.element, sign_b.element})
    element_desc, score_range = ELEMENT_COMPAT[key]
    score = random.randint(*score_range)
    text = (
        f"☀️ **Sun sign** — {sign_a.symbol} {sign_a.name} ({sign_a.element}) meets "
        f"{sign_b.symbol} {sign_b.name} ({sign_b.element}). {element_desc} "
        f"{_quality_note(sign_a, sign_b)}"
    )
    return score, text


# ----------------------------------------------------------- chinese zodiac

# The four trines: each is a natural affinity group of three animals.
_TRINES = [
    frozenset({"Rat", "Dragon", "Monkey"}),
    frozenset({"Ox", "Snake", "Rooster"}),
    frozenset({"Tiger", "Horse", "Dog"}),
    frozenset({"Rabbit", "Goat", "Pig"}),
]

# "Secret friends" — a traditional pairing even tighter than a trine.
_SECRET_FRIENDS = {
    frozenset({"Rat", "Ox"}), frozenset({"Tiger", "Pig"}),
    frozenset({"Rabbit", "Dog"}), frozenset({"Dragon", "Rooster"}),
    frozenset({"Snake", "Monkey"}), frozenset({"Horse", "Goat"}),
}

# Direct opposites on the zodiac wheel — the classic clashes.
_CLASHES = {
    frozenset({"Rat", "Horse"}), frozenset({"Ox", "Goat"}),
    frozenset({"Tiger", "Monkey"}), frozenset({"Rabbit", "Rooster"}),
    frozenset({"Dragon", "Dog"}), frozenset({"Snake", "Pig"}),
}


def _animal_component(animal_a: str, animal_b: str) -> tuple[int, str]:
    if animal_a == animal_b:
        return random.randint(55, 78), (
            f"Two {animal_a}s recognize their own reflection instantly — "
            f"comfortable, if a little too familiar to surprise each other."
        )
    pair = frozenset({animal_a, animal_b})
    if pair in _SECRET_FRIENDS:
        return random.randint(80, 97), (
            f"{animal_a} and {animal_b} are secret friends in the Chinese "
            f"zodiac — a quiet, near-effortless alliance."
        )
    for trine in _TRINES:
        if animal_a in trine and animal_b in trine:
            return random.randint(72, 92), (
                f"{animal_a} and {animal_b} share a trine — one of the four "
                f"natural affinity groups of the Chinese zodiac."
            )
    if pair in _CLASHES:
        return random.randint(10, 34), (
            f"{animal_a} and {animal_b} sit in direct opposition on the "
            f"zodiac wheel — a classic clash."
        )
    return random.randint(42, 66), (
        f"{animal_a} and {animal_b} have no special bond on the zodiac "
        f"wheel — not enemies, not fated, just two animals at the same table."
    )


# Wu Xing five-element cycle. Generative (good): Wood -> Fire -> Earth ->
# Metal -> Water -> Wood. Destructive (bad): Wood -> Earth -> Water -> Fire
# -> Metal -> Wood. (description, (low, high) percentage range)
CHINESE_ELEMENT_COMPAT: dict[frozenset, tuple[str, tuple[int, int]]] = {
    frozenset({"Wood"}): (
        "two Wood elements grow in the same direction — plenty of ambition, "
        "occasionally competing for the same sunlight.",
        (48, 72),
    ),
    frozenset({"Fire"}): (
        "two Fire elements together burn bright and fast — thrilling, and a "
        "little combustible.",
        (48, 72),
    ),
    frozenset({"Earth"}): (
        "two Earth elements build slow and steady — comfortable, if a "
        "little too content to stay put.",
        (48, 72),
    ),
    frozenset({"Metal"}): (
        "two Metal elements are both precise and unyielding — total mutual "
        "respect, and neither one bends first.",
        (48, 72),
    ),
    frozenset({"Water"}): (
        "two Water elements flow around each other easily — intuitive, "
        "though occasionally directionless together.",
        (48, 72),
    ),
    frozenset({"Wood", "Fire"}): (
        "Wood feeds Fire — one supplies the fuel, the other brings the "
        "spark. A natural, easy generative pairing.",
        (65, 92),
    ),
    frozenset({"Fire", "Earth"}): (
        "Fire's ashes become Earth — warmth that settles into something "
        "lasting.",
        (65, 92),
    ),
    frozenset({"Earth", "Metal"}): (
        "Earth quietly gives rise to Metal — patience rewarded with "
        "precision.",
        (65, 92),
    ),
    frozenset({"Metal", "Water"}): (
        "Metal collects Water like dew on a blade — a clarifying, refining "
        "match.",
        (65, 92),
    ),
    frozenset({"Water", "Wood"}): (
        "Water nourishes Wood's roots — quiet support that lets the other "
        "grow tall.",
        (65, 92),
    ),
    frozenset({"Wood", "Earth"}): (
        "Wood roots crack through Earth — growth that comes at the other's "
        "expense.",
        (12, 38),
    ),
    frozenset({"Earth", "Water"}): (
        "Earth dams and muddies Water — stability on one side reads as "
        "stagnation on the other.",
        (12, 38),
    ),
    frozenset({"Water", "Fire"}): (
        "Water douses Fire on contact — one side's calm reads as the "
        "other's total shutdown.",
        (12, 38),
    ),
    frozenset({"Fire", "Metal"}): (
        "Fire melts Metal down — passion that overwhelms precision.",
        (12, 38),
    ),
    frozenset({"Metal", "Wood"}): (
        "Metal cuts through Wood — discipline that leaves growth nowhere "
        "to go.",
        (12, 38),
    ),
}


def _chinese_element_component(elem_a: str, elem_b: str) -> tuple[int, str]:
    key = frozenset({elem_a, elem_b})
    desc, score_range = CHINESE_ELEMENT_COMPAT[key]
    return random.randint(*score_range), desc


def _chinese_component(
    animal_a: str, elem_a: str, animal_b: str, elem_b: str
) -> tuple[int, str]:
    animal_score, animal_text = _animal_component(animal_a, animal_b)
    element_score, element_text = _chinese_element_component(elem_a, elem_b)
    score = round((animal_score + element_score) / 2)
    emoji = ANIMAL_EMOJI.get(animal_a, "🀄")
    text = (
        f"{emoji} **Chinese zodiac** — {animal_a} meets {animal_b}. "
        f"{animal_text} And elementally, {element_text}"
    )
    return score, text


# ---------------------------------------------------------------- blood type

# Popular ABO blood-type compatibility lore, keyed by the unordered pair of
# type keys. (description, (low, high) percentage range)
BLOOD_COMPAT: dict[frozenset, tuple[str, tuple[int, int]]] = {
    frozenset({"a"}): (
        "run an impressively organized table together — though neither one "
        "wants to be the first to relax.",
        (50, 74),
    ),
    frozenset({"b"}): (
        "chase whatever's interesting in the same direction at the same "
        "time — chaotic, but never boring.",
        (55, 80),
    ),
    frozenset({"ab"}): (
        "share a quiet, slightly detached understanding of each other — "
        "respectful, a little reserved.",
        (48, 70),
    ),
    frozenset({"o"}): (
        "both want to lead the table — plenty of chemistry, plenty of "
        "friendly competition.",
        (50, 78),
    ),
    frozenset({"a", "o"}): (
        "click fast — Type O's confidence puts Type A instantly at ease, "
        "one of the most popular pairings in blood-type lore.",
        (68, 95),
    ),
    frozenset({"a", "b"}): (
        "grate on each other — Type A's plans meet Type B's total "
        "disregard for plans. Exhausting for one, exhilarating for the other.",
        (20, 45),
    ),
    frozenset({"a", "ab"}): (
        "settle each other — Type AB's calm detachment is oddly steadying "
        "for Type A's careful nerves.",
        (58, 84),
    ),
    frozenset({"b", "o"}): (
        "spark hard — two strong, independent personalities pulling in "
        "their own directions. Magnetic, occasionally a collision.",
        (55, 88),
    ),
    frozenset({"b", "ab"}): (
        "understand each other rarely well — Type AB is one of the few "
        "types that doesn't try to rein Type B in.",
        (60, 86),
    ),
    frozenset({"o", "ab"}): (
        "circle each other curiously — Type O is drawn to what it can't "
        "quite figure out, and Type AB is happy to stay a little mysterious.",
        (45, 78),
    ),
}


def _blood_component(blood_a: str, blood_b: str) -> tuple[int, str]:
    key = frozenset({blood_a, blood_b})
    desc, score_range = BLOOD_COMPAT[key]
    score = random.randint(*score_range)
    label_a = BLOOD_TYPES[blood_a].label
    label_b = BLOOD_TYPES[blood_b].label
    if blood_a == blood_b:
        text = f"🩸 **Blood type** — two {label_a}s {desc}"
    else:
        text = f"🩸 **Blood type** — {label_a} and {label_b} {desc}"
    return score, text


# ----------------------------------------------------------------- flavor

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
        description="Check compatibility between two members (defaults to you).",
    )
    @app_commands.describe(
        member="Who to check compatibility with",
        as_member="Check as this member instead of yourself (optional)",
    )
    @app_commands.guild_only()
    async def compatibility(
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
                "You can't check someone's compatibility with themselves — "
                "pick two different people.",
                ephemeral=True,
            )
            return

        # The one real exception, either direction. Always names them the
        # same way — Trimalchio first, Gwendalini second — no matter who
        # actually ran the command or which two members were picked.
        if {person_a.id, person_b.id} == SOULMATE_PAIR:
            people = {person_a.id: person_a, person_b.id: person_b}
            trimalchio_user = people[TRIMALCHIO_ID]
            gwendalini_user = people[GWENDALINI_ID]

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

        data_a = await self.db.get_user(guild.id, person_a.id) or {}
        data_b = await self.db.get_user(guild.id, person_b.id) or {}

        sign_a = get_sign(data_a.get("sun_sign")) if data_a.get("sun_sign") else None
        sign_b = get_sign(data_b.get("sun_sign")) if data_b.get("sun_sign") else None

        animal_a, elem_a = data_a.get("chinese_animal"), data_a.get("chinese_element")
        animal_b, elem_b = data_b.get("chinese_animal"), data_b.get("chinese_element")

        blood_a, blood_b = data_a.get("blood_type"), data_b.get("blood_type")

        components: list[tuple[int, str]] = []
        missing_notes: list[str] = []

        if sign_a and sign_b:
            components.append(_sun_component(sign_a, sign_b))
        else:
            who = person_a.mention if not sign_a else person_b.mention
            missing_notes.append(f"a Sun sign from {who} (`/placements` or the verification panel)")

        if animal_a and elem_a and animal_b and elem_b:
            components.append(_chinese_component(animal_a, elem_a, animal_b, elem_b))
        else:
            who = person_a.mention if not (animal_a and elem_a) else person_b.mention
            missing_notes.append(f"a Chinese zodiac reading from {who} (`/chinesezodiac`)")

        if blood_a in BLOOD_TYPES and blood_b in BLOOD_TYPES:
            components.append(_blood_component(blood_a, blood_b))
        else:
            who = person_a.mention if blood_a not in BLOOD_TYPES else person_b.mention
            missing_notes.append(f"a blood type from {who} (`/bloodtype`)")

        if components:
            overall = round(sum(score for score, _ in components) / len(components))
            reading = "\n\n".join(text for _, text in components)
            reading += f"\n\n**Overall compatibility: {overall}%**"
            if missing_notes:
                reading += (
                    "\n\n*(The reading would run even deeper with "
                    + "; ".join(missing_notes) + ".)*"
                )
        else:
            overall = random.randint(4, 61)
            reading = (
                f"{person_a.mention} and {person_b.mention} — **{overall}%** compatible.\n\n"
                f"*(Neither of you has enough on file yet for a real reading. Missing: "
                + "; ".join(missing_notes) + ".)*"
            )

        twist = random.choice(TWIST_LINES)

        # Normally the joke redirects everyone's "true match" to Trimalchio.
        # That breaks down when Trimalchio himself is the subject of the
        # reading (the Trimalchio+Gwendalini pairing is already handled
        # above and never reaches this point) — "Trimalchio + Trimalchio:
        # 100%" makes no sense, so he gets his own finale instead.
        if person_a.id == TRIMALCHIO_ID:
            finale = random.choice(TRIMALCHIO_ASKER_LINES).format(target=person_b.mention)
        else:
            finale = f"**{person_a.mention} + Trimalchio: 💯% compatible.**"

        description = (
            f"{reading}\n\n"
            f"{twist} Your true match was here all along.\n\n"
            f"{finale}\n\n"
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
